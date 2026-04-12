import { useQuery } from '@tanstack/react-query';
import { fetchAllSkills, getCategories } from '../api/github';
import { createLogger } from '../lib/logger';
import type { CategoryWithCount } from '../types';

const log = createLogger('hook:useCategories');

export function useCategories() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: async (): Promise<CategoryWithCount[]> => {
      log.debug('Fetching categories');
      const skills = await fetchAllSkills();
      const categories = getCategories(skills);
      log.info('Categories resolved', { count: categories.length });
      return categories;
    },
    staleTime: 1000 * 60 * 30,
  });
}
