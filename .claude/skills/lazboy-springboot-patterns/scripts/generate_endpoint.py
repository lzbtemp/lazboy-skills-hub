#!/usr/bin/env python3
"""Generate Spring Boot REST endpoint boilerplate.

Creates controller, service, repository, DTO, and test files for a new
REST resource following Spring Boot best practices.

Usage:
    python generate_endpoint.py Product --package com.lazboy.products
    python generate_endpoint.py Order --package com.lazboy.orders --output ./src
    python generate_endpoint.py Customer --package com.lazboy.crm --fields "name:String,email:String,phone:String"
"""

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent


@dataclass
class FieldDef:
    name: str
    java_type: str

    @property
    def capitalized(self) -> str:
        return self.name[0].upper() + self.name[1:]

    @property
    def validation_annotation(self) -> str:
        if self.java_type == "String":
            return "@NotBlank"
        elif self.java_type in ("BigDecimal", "Double", "Float"):
            return "@NotNull @Positive"
        elif self.java_type in ("Long", "Integer"):
            return "@NotNull"
        else:
            return "@NotNull"


@dataclass
class EndpointConfig:
    entity_name: str
    package_name: str
    fields: list[FieldDef]
    output_dir: Path
    api_version: str = "v1"

    @property
    def entity_lower(self) -> str:
        return self.entity_name[0].lower() + self.entity_name[1:]

    @property
    def entity_plural(self) -> str:
        name = self.entity_lower
        if name.endswith("y"):
            return name[:-1] + "ies"
        elif name.endswith("s") or name.endswith("x") or name.endswith("z"):
            return name + "es"
        return name + "s"

    @property
    def package_path(self) -> str:
        return self.package_name.replace(".", "/")

    @property
    def api_path(self) -> str:
        return f"/api/{self.api_version}/{self.entity_plural}"


def generate_entity(config: EndpointConfig) -> str:
    fields = ""
    for f in config.fields:
        fields += f"\n    private {f.java_type} {f.name};\n"

    return dedent(f"""\
        package {config.package_name}.model;

        import jakarta.persistence.*;
        import lombok.*;
        import org.springframework.data.annotation.CreatedDate;
        import org.springframework.data.annotation.LastModifiedDate;
        import org.springframework.data.jpa.domain.support.AuditingEntityListener;

        import java.math.BigDecimal;
        import java.time.LocalDateTime;

        @Entity
        @Table(name = "{config.entity_plural}")
        @EntityListeners(AuditingEntityListener.class)
        @Getter
        @Setter
        @Builder
        @NoArgsConstructor
        @AllArgsConstructor
        public class {config.entity_name} {{

            @Id
            @GeneratedValue(strategy = GenerationType.IDENTITY)
            private Long id;
        {fields}
            @CreatedDate
            @Column(updatable = false)
            private LocalDateTime createdAt;

            @LastModifiedDate
            private LocalDateTime updatedAt;
        }}
    """)


def generate_dto(config: EndpointConfig) -> str:
    params = "        Long id,\n"
    for f in config.fields:
        params += f"        {f.java_type} {f.name},\n"
    params += "        LocalDateTime createdAt"

    from_fields = "                entity.getId(),\n"
    for f in config.fields:
        from_fields += f"                entity.get{f.capitalized}(),\n"
    from_fields += "                entity.getCreatedAt()"

    return dedent(f"""\
        package {config.package_name}.dto;

        import {config.package_name}.model.{config.entity_name};

        import java.math.BigDecimal;
        import java.time.LocalDateTime;

        public record {config.entity_name}Dto(
        {params}) {{

            public static {config.entity_name}Dto from({config.entity_name} entity) {{
                return new {config.entity_name}Dto(
        {from_fields});
            }}
        }}
    """)


def generate_create_request(config: EndpointConfig) -> str:
    params = ""
    for i, f in enumerate(config.fields):
        annotation = f.validation_annotation
        suffix = "" if i == len(config.fields) - 1 else ","
        params += f"        {annotation} {f.java_type} {f.name}{suffix}\n"

    return dedent(f"""\
        package {config.package_name}.dto;

        import jakarta.validation.constraints.*;

        import java.math.BigDecimal;

        public record Create{config.entity_name}Request(
        {params.rstrip()}) {{}}
    """)


def generate_update_request(config: EndpointConfig) -> str:
    params = ""
    for i, f in enumerate(config.fields):
        suffix = "" if i == len(config.fields) - 1 else ","
        params += f"        {f.java_type} {f.name}{suffix}\n"

    return dedent(f"""\
        package {config.package_name}.dto;

        import java.math.BigDecimal;

        public record Update{config.entity_name}Request(
        {params.rstrip()}) {{}}
    """)


def generate_repository(config: EndpointConfig) -> str:
    return dedent(f"""\
        package {config.package_name}.repository;

        import {config.package_name}.model.{config.entity_name};
        import org.springframework.data.jpa.repository.JpaRepository;
        import org.springframework.stereotype.Repository;

        import java.util.Optional;

        @Repository
        public interface {config.entity_name}Repository extends JpaRepository<{config.entity_name}, Long> {{

            // Add custom query methods here
            // Optional<{config.entity_name}> findBySlug(String slug);
        }}
    """)


def generate_service(config: EndpointConfig) -> str:
    builder_fields = ""
    for f in config.fields:
        builder_fields += f"                .{f.name}(request.{f.name}())\n"

    update_fields = ""
    for f in config.fields:
        update_fields += f"        if (request.{f.name}() != null) {{\n"
        update_fields += f"            {config.entity_lower}.set{f.capitalized}(request.{f.name}());\n"
        update_fields += f"        }}\n"

    return dedent(f"""\
        package {config.package_name}.service;

        import {config.package_name}.dto.Create{config.entity_name}Request;
        import {config.package_name}.dto.Update{config.entity_name}Request;
        import {config.package_name}.dto.{config.entity_name}Dto;
        import {config.package_name}.model.{config.entity_name};
        import {config.package_name}.repository.{config.entity_name}Repository;
        import jakarta.persistence.EntityNotFoundException;
        import lombok.RequiredArgsConstructor;
        import org.springframework.data.domain.Page;
        import org.springframework.data.domain.Pageable;
        import org.springframework.stereotype.Service;
        import org.springframework.transaction.annotation.Transactional;

        @Service
        @RequiredArgsConstructor
        public class {config.entity_name}Service {{

            private final {config.entity_name}Repository {config.entity_lower}Repository;

            @Transactional(readOnly = true)
            public Page<{config.entity_name}Dto> findAll(Pageable pageable) {{
                return {config.entity_lower}Repository.findAll(pageable).map({config.entity_name}Dto::from);
            }}

            @Transactional(readOnly = true)
            public {config.entity_name}Dto findById(Long id) {{
                return {config.entity_lower}Repository.findById(id)
                        .map({config.entity_name}Dto::from)
                        .orElseThrow(() -> new EntityNotFoundException("{config.entity_name} not found: " + id));
            }}

            @Transactional
            public {config.entity_name}Dto create(Create{config.entity_name}Request request) {{
                {config.entity_name} {config.entity_lower} = {config.entity_name}.builder()
        {builder_fields}                .build();
                return {config.entity_name}Dto.from({config.entity_lower}Repository.save({config.entity_lower}));
            }}

            @Transactional
            public {config.entity_name}Dto update(Long id, Update{config.entity_name}Request request) {{
                {config.entity_name} {config.entity_lower} = {config.entity_lower}Repository.findById(id)
                        .orElseThrow(() -> new EntityNotFoundException("{config.entity_name} not found: " + id));

        {update_fields}
                return {config.entity_name}Dto.from({config.entity_lower}Repository.save({config.entity_lower}));
            }}

            @Transactional
            public void delete(Long id) {{
                if (!{config.entity_lower}Repository.existsById(id)) {{
                    throw new EntityNotFoundException("{config.entity_name} not found: " + id);
                }}
                {config.entity_lower}Repository.deleteById(id);
            }}
        }}
    """)


def generate_controller(config: EndpointConfig) -> str:
    return dedent(f"""\
        package {config.package_name}.controller;

        import {config.package_name}.dto.Create{config.entity_name}Request;
        import {config.package_name}.dto.Update{config.entity_name}Request;
        import {config.package_name}.dto.{config.entity_name}Dto;
        import {config.package_name}.service.{config.entity_name}Service;
        import jakarta.validation.Valid;
        import lombok.RequiredArgsConstructor;
        import org.springframework.data.domain.Page;
        import org.springframework.data.domain.PageRequest;
        import org.springframework.data.domain.Pageable;
        import org.springframework.data.domain.Sort;
        import org.springframework.http.ResponseEntity;
        import org.springframework.web.bind.annotation.*;

        import java.net.URI;

        @RestController
        @RequestMapping("{config.api_path}")
        @RequiredArgsConstructor
        public class {config.entity_name}Controller {{

            private final {config.entity_name}Service {config.entity_lower}Service;

            @GetMapping
            public ResponseEntity<Page<{config.entity_name}Dto>> list(
                    @RequestParam(defaultValue = "0") int page,
                    @RequestParam(defaultValue = "20") int size,
                    @RequestParam(defaultValue = "id") String sort) {{
                Pageable pageable = PageRequest.of(page, size, Sort.by(sort));
                return ResponseEntity.ok({config.entity_lower}Service.findAll(pageable));
            }}

            @GetMapping("/{{id}}")
            public ResponseEntity<{config.entity_name}Dto> getById(@PathVariable Long id) {{
                return ResponseEntity.ok({config.entity_lower}Service.findById(id));
            }}

            @PostMapping
            public ResponseEntity<{config.entity_name}Dto> create(
                    @Valid @RequestBody Create{config.entity_name}Request request) {{
                {config.entity_name}Dto created = {config.entity_lower}Service.create(request);
                URI location = URI.create("{config.api_path}/" + created.id());
                return ResponseEntity.created(location).body(created);
            }}

            @PutMapping("/{{id}}")
            public ResponseEntity<{config.entity_name}Dto> update(
                    @PathVariable Long id,
                    @Valid @RequestBody Update{config.entity_name}Request request) {{
                return ResponseEntity.ok({config.entity_lower}Service.update(id, request));
            }}

            @DeleteMapping("/{{id}}")
            public ResponseEntity<Void> delete(@PathVariable Long id) {{
                {config.entity_lower}Service.delete(id);
                return ResponseEntity.noContent().build();
            }}
        }}
    """)


def generate_controller_test(config: EndpointConfig) -> str:
    json_fields = ""
    for f in config.fields:
        if f.java_type == "String":
            json_fields += f'            "{f.name}": "test-{f.name}"'
        elif f.java_type == "BigDecimal":
            json_fields += f'            "{f.name}": 99.99'
        elif f.java_type in ("Long", "Integer"):
            json_fields += f'            "{f.name}": 1'
        elif f.java_type == "Boolean":
            json_fields += f'            "{f.name}": true'
        else:
            json_fields += f'            "{f.name}": "test"'
        json_fields += ",\n"
    json_fields = json_fields.rstrip(",\n")

    return dedent(f"""\
        package {config.package_name}.controller;

        import {config.package_name}.dto.{config.entity_name}Dto;
        import {config.package_name}.service.{config.entity_name}Service;
        import jakarta.persistence.EntityNotFoundException;
        import org.junit.jupiter.api.Test;
        import org.springframework.beans.factory.annotation.Autowired;
        import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
        import org.springframework.boot.test.mock.bean.MockBean;
        import org.springframework.http.MediaType;
        import org.springframework.test.web.servlet.MockMvc;

        import java.math.BigDecimal;
        import java.time.LocalDateTime;

        import static org.mockito.ArgumentMatchers.any;
        import static org.mockito.Mockito.when;
        import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
        import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

        @WebMvcTest({config.entity_name}Controller.class)
        class {config.entity_name}ControllerTest {{

            @Autowired
            private MockMvc mockMvc;

            @MockBean
            private {config.entity_name}Service {config.entity_lower}Service;

            @Test
            void getById_Existing_Returns200() throws Exception {{
                {config.entity_name}Dto dto = createTestDto();
                when({config.entity_lower}Service.findById(1L)).thenReturn(dto);

                mockMvc.perform(get("{config.api_path}/1"))
                        .andExpect(status().isOk())
                        .andExpect(jsonPath("$.id").value(1));
            }}

            @Test
            void getById_NotFound_Returns404() throws Exception {{
                when({config.entity_lower}Service.findById(99L))
                        .thenThrow(new EntityNotFoundException("{config.entity_name} not found: 99"));

                mockMvc.perform(get("{config.api_path}/99"))
                        .andExpect(status().isNotFound());
            }}

            @Test
            void create_ValidRequest_Returns201() throws Exception {{
                {config.entity_name}Dto dto = createTestDto();
                when({config.entity_lower}Service.create(any())).thenReturn(dto);

                mockMvc.perform(post("{config.api_path}")
                                .contentType(MediaType.APPLICATION_JSON)
                                .content(\\"\\"\\"
                                    {{
        {json_fields}
                                    }}
                                    \\"\\"\\""))
                        .andExpect(status().isCreated())
                        .andExpect(header().exists("Location"));
            }}

            @Test
            void delete_Returns204() throws Exception {{
                mockMvc.perform(delete("{config.api_path}/1"))
                        .andExpect(status().isNoContent());
            }}

            private {config.entity_name}Dto createTestDto() {{
                // Construct a test DTO with sample values
                return new {config.entity_name}Dto(1L, {', '.join('"test"' if f.java_type == 'String' else 'new BigDecimal("99.99")' if f.java_type == 'BigDecimal' else '1' if f.java_type in ('Long', 'Integer') else 'true' for f in config.fields)}, LocalDateTime.now());
            }}
        }}
    """)


def parse_fields(fields_str: str) -> list[FieldDef]:
    """Parse field definitions from 'name:Type,name:Type' format."""
    fields = []
    if not fields_str:
        return [
            FieldDef("name", "String"),
            FieldDef("description", "String"),
        ]
    for part in fields_str.split(","):
        part = part.strip()
        if ":" in part:
            name, java_type = part.split(":", 1)
            fields.append(FieldDef(name.strip(), java_type.strip()))
        else:
            fields.append(FieldDef(part.strip(), "String"))
    return fields


def write_file(filepath: Path, content: str, dry_run: bool = False) -> None:
    """Write content to file, creating parent directories."""
    if dry_run:
        print(f"[DRY RUN] Would write: {filepath}")
        return
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    print(f"  Created: {filepath}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Spring Boot REST endpoint boilerplate (controller, service, repository, DTO, tests).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s Product --package com.lazboy.products
  %(prog)s Order --package com.lazboy.orders --output ./generated
  %(prog)s Customer --package com.lazboy.crm --fields "name:String,email:String,phone:String"
  %(prog)s Product --package com.lazboy.products --dry-run
        """,
    )
    parser.add_argument(
        "entity",
        help="Entity name in PascalCase (e.g., Product, Order, Customer)",
    )
    parser.add_argument(
        "--package", "-p",
        required=True,
        help="Java package name (e.g., com.lazboy.products)",
    )
    parser.add_argument(
        "--fields", "-F",
        default="",
        help='Entity fields as "name:Type,name:Type" (default: name:String,description:String)',
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("."),
        help="Output root directory (default: current directory)",
    )
    parser.add_argument(
        "--api-version",
        default="v1",
        help="API version prefix (default: v1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files",
    )

    args = parser.parse_args()

    fields = parse_fields(args.fields)
    config = EndpointConfig(
        entity_name=args.entity,
        package_name=args.package,
        fields=fields,
        output_dir=args.output.resolve(),
        api_version=args.api_version,
    )

    print(f"Generating Spring Boot endpoint for: {config.entity_name}")
    print(f"  Package: {config.package_name}")
    print(f"  API Path: {config.api_path}")
    print(f"  Fields: {', '.join(f'{f.name}:{f.java_type}' for f in config.fields)}")
    print()

    base = config.output_dir / "src" / "main" / "java" / config.package_path
    test_base = config.output_dir / "src" / "test" / "java" / config.package_path

    files = {
        base / "model" / f"{config.entity_name}.java": generate_entity(config),
        base / "dto" / f"{config.entity_name}Dto.java": generate_dto(config),
        base / "dto" / f"Create{config.entity_name}Request.java": generate_create_request(config),
        base / "dto" / f"Update{config.entity_name}Request.java": generate_update_request(config),
        base / "repository" / f"{config.entity_name}Repository.java": generate_repository(config),
        base / "service" / f"{config.entity_name}Service.java": generate_service(config),
        base / "controller" / f"{config.entity_name}Controller.java": generate_controller(config),
        test_base / "controller" / f"{config.entity_name}ControllerTest.java": generate_controller_test(config),
    }

    for filepath, content in files.items():
        write_file(filepath, content, dry_run=args.dry_run)

    print(f"\nGenerated {len(files)} files for {config.entity_name} endpoint.")
    if not args.dry_run:
        print("Remember to add necessary dependencies to your pom.xml/build.gradle.")


if __name__ == "__main__":
    main()
