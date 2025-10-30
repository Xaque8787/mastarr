from typing import Any, Dict
from models.database import GlobalSettings
from utils.path_resolver import PathResolver
from utils.logger import get_logger

logger = get_logger("mastarr.template_expander")


class TemplateExpander:
    """
    Expands template variables in blueprint defaults.

    Supported template variables:
    - ${GLOBAL.PUID} → Global PUID setting
    - ${GLOBAL.PGID} → Global PGID setting
    - ${GLOBAL.TIMEZONE} → Global timezone setting
    - ${GLOBAL.NETWORK_NAME} → Global network name
    - ${GLOBAL.NETWORK_SUBNET} → Global network subnet
    - ${GLOBAL.NETWORK_GATEWAY} → Global network gateway
    - ${APP.HOST_PATH} → Host path for this app's stack
    - ${APP.NAME} → App name (db_name)
    """

    def __init__(self, global_settings: GlobalSettings, app_name: str):
        self.global_settings = global_settings
        self.app_name = app_name
        self.path_resolver = PathResolver()

    def expand_value(self, value: Any) -> Any:
        """
        Recursively expand template variables in any value.

        Args:
            value: Any value (string, dict, list, etc.)

        Returns:
            Value with template variables expanded
        """
        if isinstance(value, str):
            return self._expand_string(value)
        elif isinstance(value, dict):
            return {k: self.expand_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.expand_value(v) for v in value]
        else:
            return value

    def _expand_string(self, text: str) -> Any:
        """
        Expand template variables in a string.

        Args:
            text: String potentially containing template variables

        Returns:
            String with variables expanded, or converted type if entire string was a variable
        """
        original_text = text

        # Global settings
        if '${GLOBAL.PUID}' in text:
            text = text.replace('${GLOBAL.PUID}', str(self.global_settings.puid))
        if '${GLOBAL.PGID}' in text:
            text = text.replace('${GLOBAL.PGID}', str(self.global_settings.pgid))
        if '${GLOBAL.TIMEZONE}' in text:
            text = text.replace('${GLOBAL.TIMEZONE}', self.global_settings.timezone)
        if '${GLOBAL.NETWORK_NAME}' in text:
            text = text.replace('${GLOBAL.NETWORK_NAME}', self.global_settings.network_name)
        if '${GLOBAL.NETWORK_SUBNET}' in text:
            text = text.replace('${GLOBAL.NETWORK_SUBNET}', self.global_settings.network_subnet)
        if '${GLOBAL.NETWORK_GATEWAY}' in text:
            text = text.replace('${GLOBAL.NETWORK_GATEWAY}', self.global_settings.network_gateway)

        # App-specific
        if '${APP.HOST_PATH}' in text:
            host_path = self.path_resolver.get_host_stack_path(self.app_name)
            text = text.replace('${APP.HOST_PATH}', host_path)
        if '${APP.NAME}' in text:
            text = text.replace('${APP.NAME}', self.app_name)

        # If the entire string was a template variable and resulted in a number, convert it
        if original_text != text and text.isdigit():
            return int(text)

        return text

    def expand_blueprint_schema(self, blueprint_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expand all template variables in a blueprint schema definition.

        Args:
            blueprint_schema: Blueprint schema dictionary (the "schema" field)

        Returns:
            Expanded blueprint schema with template variables replaced
        """
        expanded = {}

        for field_name, field_config in blueprint_schema.items():
            expanded[field_name] = field_config.copy()

            # Expand default value
            if 'default' in expanded[field_name]:
                expanded[field_name]['default'] = self.expand_value(
                    expanded[field_name]['default']
                )

            # Expand schema routing path (e.g., "compose.networks.${GLOBAL.NETWORK_NAME}")
            if 'schema' in expanded[field_name]:
                expanded[field_name]['schema'] = self.expand_value(
                    expanded[field_name]['schema']
                )

            # Expand nested fields (for compound fields)
            if 'fields' in expanded[field_name]:
                expanded[field_name]['fields'] = self.expand_blueprint_schema(
                    expanded[field_name]['fields']
                )

            # Expand item_schema (for array fields)
            if 'item_schema' in expanded[field_name]:
                expanded[field_name]['item_schema'] = self.expand_value(
                    expanded[field_name]['item_schema']
                )

        logger.debug(f"Template expansion completed for {self.app_name}")
        return expanded

    def apply_defaults_to_inputs(
        self,
        inputs: Dict[str, Any],
        expanded_schema: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply expanded default values to user inputs where not provided.

        Args:
            inputs: User-provided input values
            expanded_schema: Blueprint schema with template variables already expanded

        Returns:
            Complete inputs with defaults applied
        """
        complete_inputs = inputs.copy()

        for field_name, field_config in expanded_schema.items():
            # Skip if user provided a value
            if field_name in complete_inputs and complete_inputs[field_name] is not None:
                continue

            # Apply default if available
            if 'default' in field_config and field_config['default'] is not None:
                complete_inputs[field_name] = field_config['default']

        return complete_inputs
