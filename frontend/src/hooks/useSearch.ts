import { useQuery } from '@tanstack/react-query';
import { searchSkills } from '../api/github';
import { createLogger } from '../lib/logger';
import type { PaginatedResponse, SkillListItem } from '../types';

const log = createLogger('hook:useSearch');

interface UseSearchParams {
  query: string;
  category?: string;
  page?: number;
  perPage?: number;
}

export function useSearch({ query, category, page = 1, perPage = 20 }: UseSearchParams) {
  return useQuery({
    queryKey: ['search', { query, category, page, perPage }],
    queryFn: async (): Promise<PaginatedResponse<SkillListItem>> => {
      log.debug('Searching skills', { query, category, page });
      let results = await searchSkills(query);

      if (category) {
        results = results.filter(s => s.category.slug === category);
      }

      const total = results.length;
      const totalPages = Math.max(1, Math.ceil(total / perPage));
      const start = (page - 1) * perPage;
      const data = results.slice(start, start + perPage);

      log.info('Search query resolved', { query, total, returned: data.length });
      return { data, page, per_page: perPage, total, total_pages: totalPages };
    },
    enabled: query.length > 0,
  });
}
