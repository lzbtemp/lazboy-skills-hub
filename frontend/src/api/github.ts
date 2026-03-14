const GITHUB_ORG = 'lzbtemp';
const GITHUB_REPO = 'lazboy-agent-skills';
const GITHUB_BRANCH = 'main';
const SKILLS_PATH = 'skills';

const RAW_BASE = `https://raw.githubusercontent.com/${GITHUB_ORG}/${GITHUB_REPO}/${GITHUB_BRANCH}`;
const API_BASE = `https://api.github.com/repos/${GITHUB_ORG}/${GITHUB_REPO}`;

interface GitHubContent {
  name: string;
  type: 'file' | 'dir';
  path: string;
}

interface SkillFrontmatter {
  name: string;
  description: string;
  version?: string;
  category?: string;
  tags?: string[];
}

function parseFrontmatter(markdown: string): { meta: SkillFrontmatter; content: string } {
  const match = markdown.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
  if (!match) {
    return { meta: { name: '', description: '' }, content: markdown };
  }

  const frontmatter = match[1];
  const content = match[2];

  const name = (frontmatter.match(/^name:\s*(.+)$/m) || [])[1]?.trim().replace(/^["']|["']$/g, '') || '';
  const descMatch = frontmatter.match(/^description:\s*["']?([\s\S]*?)["']?\s*$/m);
  const description = descMatch ? descMatch[1].replace(/\s+/g, ' ').trim() : '';
  const version = (frontmatter.match(/^version:\s*(.+)$/m) || [])[1]?.trim() || '1.0.0';
  const category = (frontmatter.match(/^category:\s*(.+)$/m) || [])[1]?.trim() || 'development';
  const tagsMatch = frontmatter.match(/^tags:\s*\[(.+)\]$/m);
  const tags = tagsMatch ? tagsMatch[1].split(',').map(t => t.trim().replace(/^["']|["']$/g, '')) : [];

  return { meta: { name, description, version, category, tags }, content };
}

// Derive a category aligned with role selector
function deriveCategory(skillName: string): string {
  const name = skillName.toLowerCase();
  if (name.includes('brand') || name.includes('design') || name.includes('ui') || name.includes('css')) return 'Designer';
  if (name.includes('test') || name.includes('playwright') || name.includes('qa')) return 'QA/Testing';
  if (name.includes('security') || name.includes('scan') || name.includes('vuln')) return 'Security';
  if (name.includes('logging') || name.includes('deploy') || name.includes('docker') || name.includes('ci')) return 'DevOps';
  if (name.includes('data') || name.includes('ml') || name.includes('ai')) return 'Data/AI';
  if (name.includes('react') || name.includes('vue') || name.includes('angular') || name.includes('frontend')) return 'Frontend';
  if (name.includes('api') || name.includes('server') || name.includes('backend') || name.includes('database')) return 'Backend';
  return 'Full Stack';
}

function deriveTags(skillName: string, description: string): string[] {
  const tags: string[] = [];
  const text = `${skillName} ${description}`.toLowerCase();
  if (text.includes('frontend') || text.includes('react') || text.includes('vue') || text.includes('css')) tags.push('Frontend');
  if (text.includes('backend') || text.includes('api') || text.includes('server') || text.includes('database')) tags.push('Backend');
  if (text.includes('devops') || text.includes('deploy') || text.includes('docker') || text.includes('logging')) tags.push('DevOps');
  if (text.includes('test') || text.includes('playwright') || text.includes('qa')) tags.push('QA/Testing');
  if (text.includes('security') || text.includes('scan') || text.includes('vuln')) tags.push('Security');
  if (text.includes('data') || text.includes('ml') || text.includes('ai')) tags.push('Data/AI');
  if (text.includes('brand') || text.includes('design') || text.includes('ui')) tags.push('Designer');
  if (text.includes('python') || text.includes('code') || text.includes('standard')) tags.push('Full Stack');
  return tags.length > 0 ? tags : ['Full Stack'];
}

export async function fetchSkillList(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/contents/${SKILLS_PATH}?ref=${GITHUB_BRANCH}`);
  if (!res.ok) throw new Error(`GitHub API error: ${res.status}`);
  const data: GitHubContent[] = await res.json();
  return data.filter(item => item.type === 'dir').map(item => item.name);
}

export async function fetchSkillContent(skillName: string): Promise<string> {
  const res = await fetch(`${RAW_BASE}/${SKILLS_PATH}/${skillName}/SKILL.md`);
  if (!res.ok) throw new Error(`Skill not found: ${skillName}`);
  return res.text();
}

export interface GitHubSkill {
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
  category: { id: number; name: string; slug: string; description: string | null; icon: string | null; sort_order: number; created_at: string };
  author: { id: number; username: string; email: string; display_name: string | null; avatar_url: string | null; role: string; created_at: string };
  tags: { id: number; name: string; slug: string }[];
}

const CATEGORY_ICONS: Record<string, string> = {
  Frontend: 'monitor',
  Backend: 'server',
  'Full Stack': 'layers',
  DevOps: 'settings',
  'Data/AI': 'cpu',
  Designer: 'figma',
  'QA/Testing': 'check-circle',
  Security: 'shield',
};

function toSkill(skillName: string, markdown: string, index: number): GitHubSkill {
  const { meta } = parseFrontmatter(markdown);
  const categoryName = deriveCategory(skillName);
  const tags = deriveTags(skillName, meta.description);

  return {
    id: index + 1,
    name: meta.name || skillName,
    slug: skillName,
    description: meta.description || `La-Z-Boy ${skillName} skill`,
    content: markdown,
    version: meta.version || '1.0.0',
    install_count: 0,
    is_published: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    category: {
      id: index + 1,
      name: categoryName,
      slug: categoryName.toLowerCase(),
      description: null,
      icon: CATEGORY_ICONS[categoryName] || 'code',
      sort_order: index,
      created_at: new Date().toISOString(),
    },
    author: {
      id: 1,
      username: 'lazboy-engineering',
      email: 'engineering@la-z-boy.com',
      display_name: 'La-Z-Boy Engineering',
      avatar_url: null,
      role: 'admin',
      created_at: new Date().toISOString(),
    },
    tags: tags.map((t, i) => ({ id: i + 1, name: t, slug: t.toLowerCase().replace(/\s+/g, '-') })),
  };
}

// Cache for all skills
let skillsCache: GitHubSkill[] | null = null;

export async function fetchAllSkills(): Promise<GitHubSkill[]> {
  if (skillsCache) return skillsCache;

  const skillNames = await fetchSkillList();
  const skills = await Promise.all(
    skillNames.map(async (name, index) => {
      const markdown = await fetchSkillContent(name);
      return toSkill(name, markdown, index);
    })
  );

  skillsCache = skills;
  return skills;
}

export async function fetchSkillBySlug(slug: string): Promise<GitHubSkill | null> {
  const skills = await fetchAllSkills();
  return skills.find(s => s.slug === slug) || null;
}

export async function searchSkills(query: string): Promise<GitHubSkill[]> {
  const skills = await fetchAllSkills();
  const q = query.toLowerCase();
  return skills.filter(s =>
    s.name.toLowerCase().includes(q) ||
    s.description.toLowerCase().includes(q) ||
    s.tags.some(t => t.name.toLowerCase().includes(q))
  );
}

export interface FileTreeItem {
  name: string;
  type: 'file' | 'dir';
  children?: FileTreeItem[];
}

export async function fetchSkillFileTree(skillName: string): Promise<FileTreeItem[]> {
  const res = await fetch(`${API_BASE}/contents/${SKILLS_PATH}/${skillName}?ref=${GITHUB_BRANCH}`);
  if (!res.ok) return [];
  const items: GitHubContent[] = await res.json();

  const tree: FileTreeItem[] = [];
  for (const item of items) {
    if (item.name === 'SKILL.md') {
      tree.push({ name: item.name, type: 'file' });
    } else if (item.type === 'dir') {
      // Fetch subdirectory contents
      const subRes = await fetch(`${API_BASE}/contents/${item.path}?ref=${GITHUB_BRANCH}`);
      const subItems: GitHubContent[] = subRes.ok ? await subRes.json() : [];
      tree.push({
        name: item.name,
        type: 'dir',
        children: subItems.map(sub => ({ name: sub.name, type: sub.type })),
      });
    } else {
      tree.push({ name: item.name, type: 'file' });
    }
  }

  // Sort: directories first, then files
  tree.sort((a, b) => {
    if (a.type !== b.type) return a.type === 'dir' ? -1 : 1;
    return a.name.localeCompare(b.name);
  });

  return tree;
}

export function getCategories(skills: GitHubSkill[]) {
  const categoryMap = new Map<string, { category: GitHubSkill['category']; count: number }>();
  for (const skill of skills) {
    const existing = categoryMap.get(skill.category.slug);
    if (existing) {
      existing.count++;
    } else {
      categoryMap.set(skill.category.slug, { category: skill.category, count: 1 });
    }
  }
  return Array.from(categoryMap.values()).map(({ category, count }) => ({
    ...category,
    skill_count: count,
  }));
}
