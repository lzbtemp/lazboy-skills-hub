import { useQuery } from '@tanstack/react-query';
import { fetchAllSkills } from '../api/github';
import { createLogger } from '../lib/logger';
import type { PaginatedResponse, SkillListItem } from '../types';

const log = createLogger('hook:useSkills');

interface UseSkillsParams {
  page?: number;
  perPage?: number;
  category?: string;
  tag?: string;
  sort?: string;
}

export function useSkills({ page = 1, perPage = 20, category, tag, sort = 'newest' }: UseSkillsParams = {}) {
  return useQuery({
    queryKey: ['skills', { page, perPage, category, tag, sort }],
    queryFn: async (): Promise<PaginatedResponse<SkillListItem>> => {
      log.debug('Fetching skills', { page, category, tag, sort });
      let skills = await fetchAllSkills();

      if (category) {
        skills = skills.filter(s => s.category.slug === category);
      }
      if (tag) {
        skills = skills.filter(s => s.tags.some(t => t.slug === tag));
      }

      if (sort === 'popular') {
        skills.sort((a, b) => b.install_count - a.install_count);
      } else if (sort === 'name') {
        skills.sort((a, b) => a.name.localeCompare(b.name));
      }

      const total = skills.length;
      const totalPages = Math.max(1, Math.ceil(total / perPage));
      const start = (page - 1) * perPage;
      const data = skills.slice(start, start + perPage);

      log.info('Skills query resolved', { total, page, totalPages, returned: data.length });
      return { data, page, per_page: perPage, total, total_pages: totalPages };
    },
  });
}
