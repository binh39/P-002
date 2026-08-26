import asyncio
import json
import logging
import textwrap
import threading
import traceback
import typing as T
import warnings
from uuid import uuid4

import openai
from aiolimiter import AsyncLimiter

with warnings.catch_warnings():
    # ignore pydantic warnings https://github.com/BerriAI/litellm/issues/2832
    warnings.simplefilter('ignore')
    import litellm  # type: ignore

try:
    from promptopt_pause import ModelRateLimitPauseError, read_pause_request, request_rate_limit_pause
except ModuleNotFoundError:  # Support ``python -m src.coverup`` from the repository root.
    from src.promptopt_pause import ModelRateLimitPauseError, read_pause_request, request_rate_limit_pause

# Turn off most logging
litellm.set_verbose = False
litellm.suppress_debug_info = True
logging.getLogger().setLevel(logging.ERROR)
# Ignore unavailable parameters
litellm.drop_params = True

_model_error_log_lock = threading.Lock()


def _error_status_code(error: BaseException) -> T.Any:
    status_code = getattr(error, "status_code", None)
    if status_code is not None:
        return status_code
    response = getattr(error, "response", None)
    return getattr(response, "status_code", None)


def log_model_error(
    *,
    model: str,
    attempt: int,
    error: BaseException,
    retrying: bool,
    retry_delay_seconds: float | None = None,
) -> None:
    """Emit one redacted Cloud Logging line for every failed provider call."""
    message = " ".join(str(error).split())[:2000]
    event = {
        "event": "model_call_error",
        "model": model,
        "attempt": attempt,
        "error_type": type(error).__name__,
        "status_code": _error_status_code(error),
        "message": message,
        "retrying": retrying,
        "retry_delay_seconds": retry_delay_seconds,
    }
    with _model_error_log_lock:
        print(
            "PROMPTOPT_MODEL_ERROR " + json.dumps(event, ensure_ascii=True, default=str),
            flush=True,
        )

# Tier 5 rate limits for models; tuples indicate limit and interval in seconds
# Extracted from https://platform.openai.com/account/limits on 8/30/2024
MODEL_RATE_LIMITS = {
    'gpt-3.5-turbo': {'token': (50_000_000, 60), 'request': (10_000, 60)},
    'gpt-3.5-turbo-0125': {'token': (50_000_000, 60), 'request': (10_000, 60)},
    'gpt-3.5-turbo-1106': {'token': (50_000_000, 60), 'request': (10_000, 60)},
    'gpt-3.5-turbo-16k': {'token': (50_000_000, 60), 'request': (10_000, 60)},
    'gpt-3.5-turbo-instruct': {'token': (90_000, 60), 'request': (3_500, 60)},
    'gpt-3.5-turbo-instruct-0914': {'token': (90_000, 60), 'request': (3_500, 60)},
    'gpt-4': {'token': (1_000_000, 60), 'request': (10_000, 60)},
    'gpt-4-0314': {'token': (1_000_000, 60), 'request': (10_000, 60)},
    'gpt-4-0613': {'token': (1_000_000, 60), 'request': (10_000, 60)},
    'gpt-4-32k-0314': {'token': (150_000, 60), 'request': (1_000, 60)},
    'gpt-4-turbo': {'token': (2_000_000, 60), 'request': (10_000, 60)},
    'gpt-4-turbo-2024-04-09': {'token': (2_000_000, 60), 'request': (10_000, 60)},
    'gpt-4-turbo-preview': {'token': (2_000_000, 60), 'request': (10_000, 60)},
    'gpt-4-0125-preview': {'token': (2_000_000, 60), 'request': (10_000, 60)},
    'gpt-4-1106-preview': {'token': (2_000_000, 60), 'request': (10_000, 60)},
    'gpt-4o': {'token': (30_000_000, 60), 'request': (10_000, 60)},
    'gpt-4o-2024-05-13': {'token': (30_000_000, 60), 'request': (10_000, 60)},
    'gpt-4o-2024-08-06': {'token': (30_000_000, 60), 'request': (10_000, 60)},
    'gpt-4o-mini': {'token': (150_000_000, 60), 'request': (30_000, 60)},
    'gpt-4o-mini-2024-07-18': {'token': (150_000_000, 60), 'request': (30_000, 60)},
    'bedrock/anthropic.claude-3-haiku-20240307-v1:0': {'token': (1_000_000, 60), 'request': (10_000, 60)},
    'bedrock/anthropic.claude-3-sonnet-20240229-v1:0': {'token': (1_000_000, 60), 'request': (10_000, 60)},
    'bedrock/anthropic.claude-3-opus-20240229-v1:0': {'token': (1_000_000, 60), 'request': (10_000, 60)},
    'anthropic.claude-3-5-sonnet-20241022-v2:0': {'token': (400_000, 50), 'request': (10_000, 50)},
    'us.anthropic.claude-3-5-sonnet-20241022-v2:0': {'token': (400_000, 50), 'request': (10_000, 50)},
    'us.anthropic.claude-3-7-sonnet-20250219-v1:0': {'token': (400_000, 50), 'request': (10_000, 50)},
}

def token_rate_limit_for_model(model_name: str) -> T.Tuple[int, int] | None:
    if model_name.startswith('openai/'):
        model_name = model_name[7:]

    if (model_limits := MODEL_RATE_LIMITS.get(model_name)):
        limit = model_limits.get('token')

        if not "anthropic" in model_name:
            try:
                import tiktoken
                tiktoken.encoding_for_model(model_name)
            except KeyError:
                warnings.warn(f"Unable to get encoding for {model_name}; will ignore rate limit")
                return None

        return limit

    return None

def compute_cost(usage: dict, model_name: str) -> float | None:
    from math import ceil

    if model_name.startswith('openai/'):
        model_name = model_name[7:]

    if 'prompt_tokens' in usage and 'completion_tokens' in usage:
        if (cost := litellm.model_cost.get(model_name)):
            return usage['prompt_tokens'] * cost['input_cost_per_token'] + \
                   usage['completion_tokens'] * cost['output_cost_per_token']

    return None

_token_encoding_cache: dict[str, T.Any] = dict()

def count_tokens(model_name: str, completion: dict):
    """Counts the number of tokens in a chat completion request."""
    from litellm import token_counter

    count = token_counter(model=model_name, messages=completion['messages'])

    return count

class ChatterError(Exception):
    pass

class Chatter:
    """Chats with an LLM."""
    def __init__(self, model: str) -> None:
        Chatter._validate_model(model)

        self._model = model
        self._model_temperature: float | None = None
        self._max_backoff = 64 # seconds
        self.token_rate_limit: AsyncLimiter | None
        self.set_token_rate_limit(token_rate_limit_for_model(model))
        self._add_cost = lambda cost: None
        self._log_msg = lambda ctx, msg: None
        self._log_json = lambda ctx, j: None
        self._log_usage = lambda ctx, event: None
        self._signal_retry = lambda: None
        self._functions: dict[str, dict[str, T.Any]] = dict()
        self._max_func_calls_per_chat = 50
        self._extra_request_pars: dict[str, T.Any] | None = None
        # Increase token limit for function calling models
        self._default_max_tokens = 30000

    @staticmethod
    def _validate_model(model) -> None:
        try:
            _, provider, _, _ = litellm.get_llm_provider(model)
        except litellm.exceptions.BadRequestError:
            raise ChatterError(textwrap.dedent("""
                Unknown or unsupported model.
                Please see https://docs.litellm.ai/docs/providers for supported models."""))

        result = litellm.validate_environment(model)
        if result['missing_keys']:
            if provider == 'openai':
                raise ChatterError(textwrap.dedent("""
                    You need an OpenAI key to use {model}.

                    You can get a key here: https://platform.openai.com/api-keys
                    Set the environment variable OPENAI_API_KEY to your key value
                        export OPENAI_API_KEY=<your key>"""))
            elif provider == 'bedrock':
                raise ChatterError(textwrap.dedent("""
                    To use Bedrock, you need an AWS account. Set the following environment variables:
                       export AWS_ACCESS_KEY_ID=<your key id>
                       export AWS_SECRET_ACCESS_KEY=<your secret key>
                       export AWS_REGION_NAME=us-west-2

                    You also need to request access to Claude:
                       https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html#manage-model-access"""))
            else:
                raise ChatterError(textwrap.dedent(f"""
                    You need a key (or keys) from {provider} to use {model}.
                    Set the following environment variables:
                        {', '.join(result['missing_keys'])}"""))

    def set_model_temperature(self, temperature: T.Optional[float]) -> None:
        self._model_temperature = temperature

    def set_token_rate_limit(self, limit: T.Union[T.Tuple[int, int], None]) -> None:
        if limit:
            self.token_rate_limit = AsyncLimiter(*limit)
        else:
            self.token_rate_limit = None

    def set_max_backoff(self, max_backoff: int) -> None:
        self._max_backoff = max_backoff

    def set_add_cost(self, add_cost: T.Callable) -> None:
        """Sets up a callback to indicate additional costs."""
        self._add_cost = add_cost

    def set_log_msg(self, log_msg: T.Callable[[str, str], None]) -> None:
        """Sets up a callback to write a message to the log."""
        self._log_msg = log_msg

    def set_log_json(self, log_json: T.Callable[[str, dict], None]) -> None:
        """Sets up a callback to write a json exchange to the log."""
        self._log_json = log_json

    def set_log_usage(self, log_usage: T.Callable[[str, dict], None]) -> None:
        """Emit one redacted, structured usage/cost event per provider response."""
        self._log_usage = log_usage

    def set_signal_retry(self, signal_retry: T.Callable) -> None:
        """Sets up a callback to indicate a retry."""
        self._signal_retry = signal_retry

    def set_extra_request_pars(self, request_pars: dict[str, T.Any] | None) -> None:
        """Sets additional parameters to pass into the LLM request."""
        self._extra_request_pars = request_pars

    def add_function(self, function: T.Callable) -> None:
        """Makes a function availabe to the LLM."""
        # LiteLLM's bundled capability map can lag behind newly released Vertex
        # Gemini model names. Gemini supports tools, so let the provider perform
        # the authoritative validation instead of rejecting a new alias locally.
        is_vertex_gemini = self._model.startswith("vertex_ai/gemini-")
        if not litellm.supports_function_calling(self._model) and not is_vertex_gemini:
            raise ChatterError(f"The {self._model} model does not support function calling.")

        try:
            schema = json.loads(getattr(function, "__doc__", ""))
            if 'name' not in schema:
                raise ChatterError(f"Name missing from function {function} schema.")
        except json.decoder.JSONDecodeError as e:
            raise ChatterError(f"Invalid JSON in function docstring: {e}")

        assert schema['name'] not in self._functions, f"Duplicated function name {schema['name']}"
        self._functions[schema['name']] = {"function": function, "schema": schema}

    def _request(self, messages: T.List[dict]) -> dict:
        extra_request_pars = self._extra_request_pars or {}

        # Keep a sensible default response cap, but let explicit caller settings override it.
        max_tokens_par = (
            {} if ('max_tokens' in extra_request_pars or 'max_completion_tokens' in extra_request_pars)
            else {'max_tokens': self._default_max_tokens}
        )

        return {
            'model': self._model,
            **({'temperature': self._model_temperature} if self._model_temperature is not None else {}),
            'messages': messages,
            **({'tools': [{'type': 'function', 'function': f['schema']} for f in self._functions.values()]} if self._functions else {}),
            **max_tokens_par,
            **extra_request_pars
        }

    async def _send_request(self, request: dict, ctx: object) -> litellm.ModelResponse | None:
        """Sends the LLM chat request, handling common failures and returning the response."""
        sleep = 1
        attempt = 0
        while True:
            try:
                if read_pause_request() is not None:
                    raise ModelRateLimitPauseError("Optimization pause has already been requested")
                # TODO also add request limit; could use 'await asyncio.gather(t.acquire(tokens), r.acquire())'
                # to acquire both
                if self.token_rate_limit:
                    try:
                        await self.token_rate_limit.acquire(count_tokens(self._model, request))
                    except ValueError as e:
                        self._log_msg(ctx, f"Error: too many tokens for rate limit ({e})")
                        return None # gives up this segment

                attempt += 1
                return await litellm.acreate(**request)

            except (litellm.exceptions.ServiceUnavailableError,
                    openai.RateLimitError,
                    openai.APITimeoutError) as e:

                is_rate_limit = _error_status_code(e) == 429 or isinstance(e, openai.RateLimitError)

                # This message usually indicates out of money in account
                if 'You exceeded your current quota' in str(e):
                    log_model_error(
                        model=self._model,
                        attempt=attempt,
                        error=e,
                        retrying=False,
                    )
                    self._log_msg(ctx, f"Failed: {type(e)} {e}")
                    if is_rate_limit and request_rate_limit_pause(
                        model=self._model,
                        attempt=attempt,
                        error=e,
                        force=True,
                    ):
                        raise ModelRateLimitPauseError("Model quota exhausted; optimization paused") from e
                    raise

                if is_rate_limit and request_rate_limit_pause(
                    model=self._model,
                    attempt=attempt,
                    error=e,
                ):
                    log_model_error(
                        model=self._model,
                        attempt=attempt,
                        error=e,
                        retrying=False,
                    )
                    self._log_msg(ctx, "Paused after repeated HTTP 429 responses")
                    raise ModelRateLimitPauseError("Repeated model rate limits; optimization paused") from e

                import random
                sleep = min(sleep * 2, self._max_backoff)
                sleep_time = random.uniform(sleep / 2, sleep)

                log_model_error(
                    model=self._model,
                    attempt=attempt,
                    error=e,
                    retrying=True,
                    retry_delay_seconds=round(sleep_time, 3),
                )

                self._log_msg(ctx, f"Error: {type(e)} {e} {sleep=} {sleep_time=}")

                self._signal_retry()
                await asyncio.sleep(sleep_time)

            except ModelRateLimitPauseError:
                raise

            except openai.BadRequestError as e:
                # usually "maximum context length" XXX check for this?
                log_model_error(model=self._model, attempt=attempt, error=e, retrying=False)
                self._log_msg(ctx, f"Error: {type(e)} {e}")
                return None # gives up this segment

            except openai.AuthenticationError as e:
                log_model_error(model=self._model, attempt=attempt, error=e, retrying=False)
                self._log_msg(ctx, f"Failed: {type(e)} {e}")
                raise

            except openai.APIConnectionError as e:
                # Missing SDK modules are local configuration errors and will
                # never recover by retrying. Surface them immediately instead
                # of spinning thousands of times per second.
                if "No module named" in str(e):
                    log_model_error(model=self._model, attempt=attempt, error=e, retrying=False)
                    self._log_msg(ctx, f"Failed: {type(e)} {e}")
                    raise

                import random
                sleep = min(sleep * 2, self._max_backoff)
                sleep_time = random.uniform(sleep / 2, sleep)
                log_model_error(
                    model=self._model,
                    attempt=attempt,
                    error=e,
                    retrying=True,
                    retry_delay_seconds=round(sleep_time, 3),
                )
                self._log_msg(
                    ctx,
                    f"Error: {type(e)} {e} {sleep=} {sleep_time=}",
                )
                self._signal_retry()
                await asyncio.sleep(sleep_time)

            except openai.APIError as e:
                # APIError is the base class for all API errors;
                # we may be missing a more specific handler.
                log_model_error(model=self._model, attempt=attempt, error=e, retrying=False)
                self._log_msg(ctx, f"Error: {type(e)} {e}")
                return None # gives up this segment

            except Exception as e:
                log_model_error(model=self._model, attempt=attempt, error=e, retrying=False)
                raise

    def _call_function(self, ctx: object, tool_call: litellm.ModelResponse) -> str:
        args = json.loads(tool_call.function.arguments)
        function = self._functions[tool_call.function.name]

        try:
            return str(function['function'](ctx=ctx, **args))
        except Exception as e:
            self._log_msg(ctx, f"""
Error executing function \"{tool_call.function.name}\": {e}
args:{args}

{traceback.format_exc()}
""")
            return f'Error executing function: {e}'

    async def chat(self, messages: list, *, ctx: T.Optional[object] = None) -> dict | None:
        """Chats with the LLM, sending the given messages, handling common failures and returning the response.
           Automatically calls any tool functions requested."""
        func_calls = 0
        tool_events = []
        while func_calls <= self._max_func_calls_per_chat:
            request = self._request(messages)
            self._log_json(ctx, request)

            if not (response := await self._send_request(request, ctx=ctx)):
                return None

            response_data = response.model_dump(warnings=False)
            self._log_json(ctx, response_data)
            response_cost = None
            try:
                response_cost = litellm.completion_cost(response)
                self._add_cost(response_cost)
            except Exception as e:
                # Model not mapped in litellm's cost calculator - ignore cost calculation
                if "isn't mapped yet" in str(e) or "model_cost" in str(e):
                    pass
                else:
                    raise
            try:
                from src.optimization.costs import usage_event

                self._log_usage(
                    ctx,
                    usage_event(
                        self._model,
                        getattr(response, "usage", {}),
                        response_cost=response_cost,
                        event_id=str(uuid4()),
                    ),
                )
            except Exception:
                # Accounting cannot be allowed to affect a generated test.
                pass

            if response.choices[0].finish_reason != "tool_calls":
                response_data["_coverup_tool_calls"] = tool_events
                return response_data

            # Keep provider-specific fields such as Gemini thought signatures;
            # LiteLLM uses them to construct the next function-calling turn.
            tool_message = response.choices[0].message.model_dump(warnings=False)
            tool_message["content"] = ""  # null upsets count_tokens
            messages.append(tool_message)

            for call in response.choices[0].message.tool_calls:
                func_calls += 1
                arguments = json.loads(call.function.arguments)
                result = self._call_function(ctx, call)
                tool_events.append({
                    "name": call.function.name,
                    "arguments": arguments,
                    "result": result,
                })
                messages.append({
                    'tool_call_id': call.id,
                    'role': 'tool',
                    'name': call.function.name,
                    'content': result,
                })

        self._log_msg(ctx, f"Too many function call requests, giving up")
        return None
