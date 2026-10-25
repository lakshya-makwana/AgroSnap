import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';

import { api } from '../../services/api';

export function useCrops() {
  const { i18n } = useTranslation();
  return useQuery({
    queryKey: ['crops', i18n.language],
    queryFn: () => api.crops(i18n.language).then((r) => r.items),
    staleTime: 24 * 60 * 60 * 1000,
  });
}
