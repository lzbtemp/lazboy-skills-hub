#!/usr/bin/env python3
"""Scaffold a new API endpoint with controller, service, repository, DTO, and test files.

Generates TypeScript files following a standard layered architecture pattern
for an Express.js API.

Usage:
    python generate_endpoint.py --resource product --methods GET POST PUT DELETE
    python generate_endpoint.py --resource order-item --methods GET POST --output src
    python generate_endpoint.py --resource user --methods GET POST PUT DELETE PATCH --output src
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from textwrap import dedent


def to_pascal_case(name: str) -> str:
    """Convert kebab-case or snake_case to PascalCase."""
    return "".join(word.capitalize() for word in re.split(r"[-_]", name))


def to_camel_case(name: str) -> str:
    """Convert kebab-case or snake_case to camelCase."""
    pascal = to_pascal_case(name)
    return pascal[0].lower() + pascal[1:]


def to_kebab_case(name: str) -> str:
    """Normalize to kebab-case."""
    # Handle PascalCase or camelCase
    name = re.sub(r"([A-Z])", r"-\1", name).lower().strip("-")
    # Handle snake_case
    name = name.replace("_", "-")
    # Collapse multiple hyphens
    name = re.sub(r"-+", "-", name)
    return name


def pluralize(name: str) -> str:
    """Simple English pluralization."""
    if name.endswith("y") and name[-2] not in "aeiou":
        return name[:-1] + "ies"
    if name.endswith(("s", "sh", "ch", "x", "z")):
        return name + "es"
    return name + "s"


def generate_dto(pascal: str, camel: str) -> str:
    return dedent(f"""\
        import {{ z }} from 'zod';

        // --- Schemas ---

        export const Create{pascal}Schema = z.object({{
          name: z.string().min(1).max(255),
          description: z.string().max(2000).optional(),
          // Add fields specific to {pascal}
        }});

        export const Update{pascal}Schema = Create{pascal}Schema.partial();

        export const {pascal}QuerySchema = z.object({{
          page: z.coerce.number().int().positive().default(1),
          limit: z.coerce.number().int().min(1).max(100).default(20),
          sort: z.string().optional(),
          search: z.string().optional(),
        }});

        // --- Types ---

        export type Create{pascal}Dto = z.infer<typeof Create{pascal}Schema>;
        export type Update{pascal}Dto = z.infer<typeof Update{pascal}Schema>;
        export type {pascal}QueryDto = z.infer<typeof {pascal}QuerySchema>;

        export interface {pascal}ResponseDto {{
          id: string;
          name: string;
          description: string | null;
          createdAt: string;
          updatedAt: string;
        }}

        export interface Paginated{pascal}Response {{
          data: {pascal}ResponseDto[];
          meta: {{
            page: number;
            limit: number;
            totalItems: number;
            totalPages: number;
          }};
        }}
    """)


def generate_repository(pascal: str, camel: str) -> str:
    plural_pascal = pluralize(pascal)
    return dedent(f"""\
        import {{ prisma }} from '../lib/prisma';
        import type {{ Create{pascal}Dto, Update{pascal}Dto, {pascal}QueryDto }} from './{to_kebab_case(pascal)}.dto';

        export class {pascal}Repository {{
          async findAll(query: {pascal}QueryDto) {{
            const {{ page, limit, sort, search }} = query;
            const skip = (page - 1) * limit;

            const where = search
              ? {{
                  OR: [
                    {{ name: {{ contains: search, mode: 'insensitive' as const }} }},
                    {{ description: {{ contains: search, mode: 'insensitive' as const }} }},
                  ],
                }}
              : {{}};

            const orderBy = sort
              ? {{ [sort.replace('-', '')]: sort.startsWith('-') ? 'desc' : 'asc' }}
              : {{ createdAt: 'desc' as const }};

            const [data, totalItems] = await Promise.all([
              prisma.{camel}.findMany({{ where, skip, take: limit, orderBy }}),
              prisma.{camel}.count({{ where }}),
            ]);

            return {{
              data,
              totalItems,
              totalPages: Math.ceil(totalItems / limit),
            }};
          }}

          async findById(id: string) {{
            return prisma.{camel}.findUnique({{ where: {{ id }} }});
          }}

          async create(dto: Create{pascal}Dto) {{
            return prisma.{camel}.create({{ data: dto }});
          }}

          async update(id: string, dto: Update{pascal}Dto) {{
            return prisma.{camel}.update({{ where: {{ id }}, data: dto }});
          }}

          async delete(id: string) {{
            return prisma.{camel}.delete({{ where: {{ id }} }});
          }}

          async exists(id: string): Promise<boolean> {{
            const count = await prisma.{camel}.count({{ where: {{ id }} }});
            return count > 0;
          }}
        }}
    """)


def generate_service(pascal: str, camel: str) -> str:
    return dedent(f"""\
        import {{ {pascal}Repository }} from './{to_kebab_case(pascal)}.repository';
        import {{ Errors }} from '../lib/errors';
        import type {{
          Create{pascal}Dto,
          Update{pascal}Dto,
          {pascal}QueryDto,
          {pascal}ResponseDto,
          Paginated{pascal}Response,
        }} from './{to_kebab_case(pascal)}.dto';

        export class {pascal}Service {{
          constructor(private readonly repository = new {pascal}Repository()) {{}}

          async list(query: {pascal}QueryDto): Promise<Paginated{pascal}Response> {{
            const result = await this.repository.findAll(query);

            return {{
              data: result.data.map(this.toResponseDto),
              meta: {{
                page: query.page,
                limit: query.limit,
                totalItems: result.totalItems,
                totalPages: result.totalPages,
              }},
            }};
          }}

          async getById(id: string): Promise<{pascal}ResponseDto> {{
            const entity = await this.repository.findById(id);
            if (!entity) {{
              throw Errors.notFound('{pascal}', id);
            }}
            return this.toResponseDto(entity);
          }}

          async create(dto: Create{pascal}Dto): Promise<{pascal}ResponseDto> {{
            const entity = await this.repository.create(dto);
            return this.toResponseDto(entity);
          }}

          async update(id: string, dto: Update{pascal}Dto): Promise<{pascal}ResponseDto> {{
            const exists = await this.repository.exists(id);
            if (!exists) {{
              throw Errors.notFound('{pascal}', id);
            }}
            const entity = await this.repository.update(id, dto);
            return this.toResponseDto(entity);
          }}

          async delete(id: string): Promise<void> {{
            const exists = await this.repository.exists(id);
            if (!exists) {{
              throw Errors.notFound('{pascal}', id);
            }}
            await this.repository.delete(id);
          }}

          private toResponseDto(entity: any): {pascal}ResponseDto {{
            return {{
              id: entity.id,
              name: entity.name,
              description: entity.description ?? null,
              createdAt: entity.createdAt.toISOString(),
              updatedAt: entity.updatedAt.toISOString(),
            }};
          }}
        }}
    """)


def generate_controller(pascal: str, camel: str, methods: list[str], kebab: str) -> str:
    plural_kebab = pluralize(kebab)

    lines = [
        f"import {{ Router, Request, Response, NextFunction }} from 'express';",
        f"import {{ {pascal}Service }} from './{kebab}.service';",
        f"import {{ validate }} from '../middleware/validate';",
        f"import {{",
        f"  Create{pascal}Schema,",
        f"  Update{pascal}Schema,",
        f"  {pascal}QuerySchema,",
        f"}} from './{kebab}.dto';",
        f"",
        f"const router = Router();",
        f"const service = new {pascal}Service();",
        f"",
    ]

    method_set = {m.upper() for m in methods}

    if "GET" in method_set:
        lines.extend([
            f"/**",
            f" * GET /{plural_kebab}",
            f" * List all {plural_kebab} with pagination",
            f" */",
            f"router.get('/', validate({{ query: {pascal}QuerySchema }}), async (req: Request, res: Response, next: NextFunction) => {{",
            f"  try {{",
            f"    const result = await service.list(req.query as any);",
            f"    res.json(result);",
            f"  }} catch (err) {{",
            f"    next(err);",
            f"  }}",
            f"}});",
            f"",
            f"/**",
            f" * GET /{plural_kebab}/:id",
            f" * Get a single {kebab} by ID",
            f" */",
            f"router.get('/:id', async (req: Request, res: Response, next: NextFunction) => {{",
            f"  try {{",
            f"    const result = await service.getById(req.params.id);",
            f"    res.json({{ data: result }});",
            f"  }} catch (err) {{",
            f"    next(err);",
            f"  }}",
            f"}});",
            f"",
        ])

    if "POST" in method_set:
        lines.extend([
            f"/**",
            f" * POST /{plural_kebab}",
            f" * Create a new {kebab}",
            f" */",
            f"router.post('/', validate({{ body: Create{pascal}Schema }}), async (req: Request, res: Response, next: NextFunction) => {{",
            f"  try {{",
            f"    const result = await service.create(req.body);",
            f"    res.status(201).json({{ data: result }});",
            f"  }} catch (err) {{",
            f"    next(err);",
            f"  }}",
            f"}});",
            f"",
        ])

    if "PUT" in method_set or "PATCH" in method_set:
        lines.extend([
            f"/**",
            f" * PUT /{plural_kebab}/:id",
            f" * Update an existing {kebab}",
            f" */",
            f"router.put('/:id', validate({{ body: Update{pascal}Schema }}), async (req: Request, res: Response, next: NextFunction) => {{",
            f"  try {{",
            f"    const result = await service.update(req.params.id, req.body);",
            f"    res.json({{ data: result }});",
            f"  }} catch (err) {{",
            f"    next(err);",
            f"  }}",
            f"}});",
            f"",
        ])

    if "PATCH" in method_set:
        lines.extend([
            f"/**",
            f" * PATCH /{plural_kebab}/:id",
            f" * Partially update an existing {kebab}",
            f" */",
            f"router.patch('/:id', validate({{ body: Update{pascal}Schema }}), async (req: Request, res: Response, next: NextFunction) => {{",
            f"  try {{",
            f"    const result = await service.update(req.params.id, req.body);",
            f"    res.json({{ data: result }});",
            f"  }} catch (err) {{",
            f"    next(err);",
            f"  }}",
            f"}});",
            f"",
        ])

    if "DELETE" in method_set:
        lines.extend([
            f"/**",
            f" * DELETE /{plural_kebab}/:id",
            f" * Delete a {kebab}",
            f" */",
            f"router.delete('/:id', async (req: Request, res: Response, next: NextFunction) => {{",
            f"  try {{",
            f"    await service.delete(req.params.id);",
            f"    res.status(204).send();",
            f"  }} catch (err) {{",
            f"    next(err);",
            f"  }}",
            f"}});",
            f"",
        ])

    lines.extend([
        f"export default router;",
    ])

    return "\n".join(lines)


def generate_test(pascal: str, camel: str, methods: list[str], kebab: str) -> str:
    plural_kebab = pluralize(kebab)
    method_set = {m.upper() for m in methods}

    lines = [
        f"import request from 'supertest';",
        f"import {{ app }} from '../../app';",
        f"import {{ prisma }} from '../../lib/prisma';",
        f"",
        f"describe('{pascal} API', () => {{",
        f"  const basePath = '/api/v1/{plural_kebab}';",
        f"",
        f"  const mock{pascal} = {{",
        f"    name: 'Test {pascal}',",
        f"    description: 'A test {camel} for unit tests',",
        f"  }};",
        f"",
        f"  let created{pascal}Id: string;",
        f"",
        f"  afterAll(async () => {{",
        f"    await prisma.$disconnect();",
        f"  }});",
        f"",
    ]

    if "POST" in method_set:
        lines.extend([
            f"  describe('POST /{plural_kebab}', () => {{",
            f"    it('should create a new {camel}', async () => {{",
            f"      const res = await request(app)",
            f"        .post(basePath)",
            f"        .send(mock{pascal})",
            f"        .expect(201);",
            f"",
            f"      expect(res.body.data).toMatchObject({{",
            f"        name: mock{pascal}.name,",
            f"        description: mock{pascal}.description,",
            f"      }});",
            f"      expect(res.body.data.id).toBeDefined();",
            f"      created{pascal}Id = res.body.data.id;",
            f"    }});",
            f"",
            f"    it('should return 400 for invalid input', async () => {{",
            f"      const res = await request(app)",
            f"        .post(basePath)",
            f"        .send({{ name: '' }})",
            f"        .expect(400);",
            f"",
            f"      expect(res.body.error).toBeDefined();",
            f"      expect(res.body.error.status).toBe(400);",
            f"    }});",
            f"  }});",
            f"",
        ])

    if "GET" in method_set:
        lines.extend([
            f"  describe('GET /{plural_kebab}', () => {{",
            f"    it('should return a paginated list', async () => {{",
            f"      const res = await request(app)",
            f"        .get(basePath)",
            f"        .query({{ page: 1, limit: 10 }})",
            f"        .expect(200);",
            f"",
            f"      expect(res.body.data).toBeInstanceOf(Array);",
            f"      expect(res.body.meta).toMatchObject({{",
            f"        page: 1,",
            f"        limit: 10,",
            f"      }});",
            f"    }});",
            f"  }});",
            f"",
            f"  describe('GET /{plural_kebab}/:id', () => {{",
            f"    it('should return a single {camel}', async () => {{",
            f"      const res = await request(app)",
            f"        .get(`${{basePath}}/${{created{pascal}Id}}`)",
            f"        .expect(200);",
            f"",
            f"      expect(res.body.data.id).toBe(created{pascal}Id);",
            f"    }});",
            f"",
            f"    it('should return 404 for non-existent id', async () => {{",
            f"      await request(app)",
            f"        .get(`${{basePath}}/non-existent-id`)",
            f"        .expect(404);",
            f"    }});",
            f"  }});",
            f"",
        ])

    if "PUT" in method_set or "PATCH" in method_set:
        method = "put" if "PUT" in method_set else "patch"
        lines.extend([
            f"  describe('{method.upper()} /{plural_kebab}/:id', () => {{",
            f"    it('should update an existing {camel}', async () => {{",
            f"      const res = await request(app)",
            f"        .{method}(`${{basePath}}/${{created{pascal}Id}}`)",
            f"        .send({{ name: 'Updated {pascal}' }})",
            f"        .expect(200);",
            f"",
            f"      expect(res.body.data.name).toBe('Updated {pascal}');",
            f"    }});",
            f"",
            f"    it('should return 404 for non-existent id', async () => {{",
            f"      await request(app)",
            f"        .{method}(`${{basePath}}/non-existent-id`)",
            f"        .send({{ name: 'Nope' }})",
            f"        .expect(404);",
            f"    }});",
            f"  }});",
            f"",
        ])

    if "DELETE" in method_set:
        lines.extend([
            f"  describe('DELETE /{plural_kebab}/:id', () => {{",
            f"    it('should delete an existing {camel}', async () => {{",
            f"      await request(app)",
            f"        .delete(`${{basePath}}/${{created{pascal}Id}}`)",
            f"        .expect(204);",
            f"    }});",
            f"",
            f"    it('should return 404 for non-existent id', async () => {{",
            f"      await request(app)",
            f"        .delete(`${{basePath}}/non-existent-id`)",
            f"        .expect(404);",
            f"    }});",
            f"  }});",
            f"",
        ])

    lines.extend([
        f"}});",
    ])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold a new API endpoint with controller, service, repository, DTO, and tests.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --resource product --methods GET POST PUT DELETE
  %(prog)s --resource order-item --methods GET POST --output src
  %(prog)s --resource user --methods GET POST PUT DELETE PATCH

Generated files (for --resource product --output src):
  src/product/product.dto.ts
  src/product/product.repository.ts
  src/product/product.service.ts
  src/product/product.controller.ts
  src/product/__tests__/product.controller.test.ts
        """,
    )
    parser.add_argument(
        "--resource",
        required=True,
        help="Resource name (e.g., 'product', 'order-item', 'user')",
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["GET", "POST", "PUT", "DELETE"],
        choices=["GET", "POST", "PUT", "PATCH", "DELETE"],
        type=str.upper,
        help="HTTP methods to scaffold (default: GET POST PUT DELETE)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("src"),
        help="Base output directory (default: src)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print generated files to stdout without writing",
    )

    args = parser.parse_args()

    kebab = to_kebab_case(args.resource)
    pascal = to_pascal_case(kebab)
    camel = to_camel_case(kebab)

    files = {
        f"{kebab}/{kebab}.dto.ts": generate_dto(pascal, camel),
        f"{kebab}/{kebab}.repository.ts": generate_repository(pascal, camel),
        f"{kebab}/{kebab}.service.ts": generate_service(pascal, camel),
        f"{kebab}/{kebab}.controller.ts": generate_controller(pascal, camel, args.methods, kebab),
        f"{kebab}/__tests__/{kebab}.controller.test.ts": generate_test(pascal, camel, args.methods, kebab),
    }

    if args.dry_run:
        for rel_path, content in files.items():
            print(f"\n{'=' * 60}")
            print(f"File: {args.output / rel_path}")
            print(f"{'=' * 60}")
            print(content)
        return 0

    output_base = args.output.resolve()
    created = []

    for rel_path, content in files.items():
        file_path = output_base / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        created.append(str(file_path))

    print(f"Scaffolded {pascal} endpoint with methods: {', '.join(args.methods)}")
    print(f"\nCreated files:")
    for path in created:
        print(f"  {path}")

    plural_kebab = pluralize(kebab)
    print(f"\nNext steps:")
    print(f"  1. Add the Prisma model for '{pascal}' in prisma/schema.prisma")
    print(f"  2. Register the route in your app:")
    print(f"     import {camel}Router from './{kebab}/{kebab}.controller';")
    print(f"     app.use('/api/v1/{plural_kebab}', {camel}Router);")
    print(f"  3. Customize the DTO fields in {kebab}/{kebab}.dto.ts")
    print(f"  4. Run: npx prisma migrate dev && npm test")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
