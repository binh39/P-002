type TokenProvider = () => Promise<string | null>;

let activeProvider: TokenProvider = async () => null;

export function setTokenProvider(provider: TokenProvider) {
  activeProvider = provider;
}

export function getAccessToken() {
  return activeProvider();
}
