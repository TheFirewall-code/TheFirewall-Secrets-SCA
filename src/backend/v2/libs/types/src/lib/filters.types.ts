import { FilterType } from '@firewall-backend/enums';

export type Filter = {
  key: string;

  label: string;

  type: FilterType;

  searchable: boolean;
};

export type FilterValueCount = {
  values: any[];

  total_count: number;
};
