import type { Faker } from '@faker-js/faker';

let fakerInstance: Faker | null = null;

const dynamicImport = (modulePath: string) =>
  new Function(`return import('${modulePath}')`)() as Promise<{
    faker: Faker;
  }>;

export const getFaker = async () => {
  if (!fakerInstance) {
    const module = await dynamicImport('@faker-js/faker');
    fakerInstance = module.faker;
  }
  return fakerInstance;
};
