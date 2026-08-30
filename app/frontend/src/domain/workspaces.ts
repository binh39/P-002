import type { UserRole } from "@/auth/AuthService";

export interface WorkspaceMember {
  user_id: string;
  email: string | null;
  name: string;
  role: UserRole;
  joined_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  members: WorkspaceMember[];
  created_at: string;
  updated_at: string;
}

export interface WorkspaceList {
  items: Workspace[];
  active_workspace_id: string;
}
