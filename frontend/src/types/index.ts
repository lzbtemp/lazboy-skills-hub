export interface Category {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  icon: string | null;
  sort_order: number;
  created_at: string;
}

export interface CategoryWithCount extends Category {
  skill_count: number;
}

export interface User {
  id: number;
  username: string;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  role: string;
  created_at: string;
}

export interface Tag {
  id: number;
  name: string;
  slug: string;
}

export interface Skill {
  id: number;
  name: string;
  slug: string;
  description: string;
  content: string;
  version: string;
  install_count: number;
  is_published: boolean;
  created_at: string;
  updated_at: string;
  category: Category;
  author: User;
  tags: Tag[];
}

export interface SkillListItem {
  id: number;
  name: string;
  slug: string;
  description: string;
  version: string;
  install_count: number;
  created_at: string;
  category: Category;
  author: User;
  tags: Tag[];
}

export interface PaginatedResponse<T> {
  data: T[];
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

// ── MCP Servers ──────────────────────────────────────────────

export interface McpTool {
  name: string;
  description: string;
}

export interface McpConfig {
  command: string;
  args: string[];
  env?: Record<string, string>;
}

// Flattened tool for the Tools catalog (derived from McpServer.tools)
export interface FlatTool {
  name: string;
  description: string;
  serverName: string;
  serverSlug: string;
  category: string;
  owner: string;
}

export interface McpServer {
  id: string;
  name: string;
  slug: string;
  description: string;
  category: string;
  owner: string;
  version?: string;
  capabilities?: string[];
  useCases?: string[];
  tools?: McpTool[];
  source?: string;
  npmPackage?: string;
  config?: McpConfig;
  popular?: boolean;
  usedBy?: string[];
}
