# Mastarr Documentation

This directory contains comprehensive documentation for the Mastarr application management system.

---

## Quick Links

| Document | Description |
|----------|-------------|
| [APP_TEMPLATE.md](APP_TEMPLATE.md) | Complete blueprint JSON template guide |
| [ENV_FILE_GENERATION.md](ENV_FILE_GENERATION.md) | Understanding .env files and env.* routing |
| [COMPOUND_FIELDS_DEMO.md](COMPOUND_FIELDS_DEMO.md) | Compound fields implementation overview |
| [RECENT_IMPROVEMENTS.md](RECENT_IMPROVEMENTS.md) | Latest system improvements summary |

---

## For Blueprint Authors

**Start Here:** [APP_TEMPLATE.md](APP_TEMPLATE.md)

This comprehensive guide covers:
- Blueprint JSON structure
- All field types and properties
- UI components
- Schema routing (service.*, compose.*, env.*, metadata.*)
- Compose transforms
- Template variables
- Complete examples
- Best practices

---

## Understanding Core Concepts

### Environment Files
Read: [ENV_FILE_GENERATION.md](ENV_FILE_GENERATION.md)

Learn how:
- `env.*` schema routing works
- .env files are generated for each app
- Variable substitution happens in Docker Compose
- The difference between .env vars and container environment vars

### Compound Fields
Read: [COMPOUND_FIELDS_DEMO.md](COMPOUND_FIELDS_DEMO.md)

Understand:
- How compound fields group related inputs
- Array fields for dynamic lists
- Data flow from UI to Docker Compose
- Benefits of the compound field approach

---

## Recent Changes

Read: [RECENT_IMPROVEMENTS.md](RECENT_IMPROVEMENTS.md)

Summary of recent improvements:
- Compound fields implementation
- Dynamic array fields for custom config
- Named volume support
- Network configuration refactoring
- Comprehensive documentation

---

## Documentation Structure

```
Documents/
├── README.md                    # This file
├── APP_TEMPLATE.md              # Blueprint authoring guide (1,213 lines)
├── ENV_FILE_GENERATION.md       # .env file explanation (417 lines)
├── COMPOUND_FIELDS_DEMO.md      # Compound fields demo (313 lines)
└── RECENT_IMPROVEMENTS.md       # Recent changes summary (416 lines)
```

---

## Quick Examples

### Minimal Blueprint
```json
{
  "name": "myapp",
  "display_name": "My App",
  "description": "My application",
  "category": "MANAGEMENT",
  "schema": {
    "image": {
      "type": "string",
      "ui_component": "text",
      "label": "Docker Image",
      "default": "myapp/image",
      "schema": "service.image"
    }
  }
}
```

### Compound Field Example
```json
{
  "web_port": {
    "type": "object",
    "label": "Web Port",
    "fields": {
      "host": {"type": "integer", "label": "Host Port", "default": 8080},
      "container": {"type": "integer", "label": "Container Port", "default": 8080}
    },
    "schema": "service.ports",
    "compose_transform": "port_mapping"
  }
}
```

### Dynamic Array Example
```json
{
  "custom_environment": {
    "type": "array",
    "ui_component": "key_value_pairs",
    "label": "Custom Environment Variables",
    "default": [],
    "advanced": true,
    "schema": "service.environment.*"
  }
}
```

---

## Getting Help

1. **Check the template:** [APP_TEMPLATE.md](APP_TEMPLATE.md) has detailed information
2. **Look at examples:** Review existing blueprints in `blueprints/` directory
3. **Understand concepts:** Read specialized docs on specific topics
4. **Test your blueprint:** Load it in the UI and verify it works

---

## Contributing

When adding new features or patterns:

1. Update [APP_TEMPLATE.md](APP_TEMPLATE.md) with new field types or transforms
2. Add examples showing the new functionality
3. Document any new schema routing patterns
4. Update [RECENT_IMPROVEMENTS.md](RECENT_IMPROVEMENTS.md) with changes

---

## Best Practices

From [APP_TEMPLATE.md](APP_TEMPLATE.md):

1. ✅ Use compound fields for related inputs
2. ✅ Provide sensible defaults
3. ✅ Use template variables (${GLOBAL.*})
4. ✅ Mark sensitive fields with `is_sensitive: true`
5. ✅ Organize with `advanced: true` for rarely-changed settings
6. ✅ Add helpful descriptions
7. ✅ Use hidden fields for computed values
8. ✅ Validate input with constraints (min/max values)

---

**Total Documentation:** ~2,400 lines covering all aspects of blueprint creation and system architecture.
