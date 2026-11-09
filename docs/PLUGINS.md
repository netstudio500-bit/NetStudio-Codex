# Plugin Development Guide

## Creating a Plugin

### Basic Structure

```python
from netstudio.plugins.base import BasePlugin
from netstudio.plugins.interfaces import PluginContext

class MyPlugin(BasePlugin):
    name = "my-plugin"
    version = "1.0.0"
    description = "My custom plugin"
    
    async def initialize(self, context: PluginContext) -> None:
        """Initialize the plugin."""
        self.logger.info(f"Initializing {self.name}")
    
    async def execute(self, input_data):
        """Execute the plugin logic."""
        return output_data
    
    async def cleanup(self) -> None:
        """Clean up resources."""
        self.logger.info(f"Cleaning up {self.name}")
```

### Plugin Types

#### Tool Plugin

```python
from netstudio.plugins.tool import ToolPlugin

class FileAnalyzerTool(ToolPlugin):
    name = "file-analyzer"
    
    async def execute(self, file_path: str) -> dict:
        # Analyze file
        return {"lines": 100, "complexity": "low"}
```

#### Strategy Plugin

```python
from netstudio.plugins.strategy import StrategyPlugin

class CustomStrategy(StrategyPlugin):
    name = "custom-strategy"
    
    async def plan(self, task: str) -> List[Step]:
        # Generate plan
        return [Step(...)]
```

### Installation

1. Create plugin directory
2. Implement plugin class
3. Add plugin.yaml
4. Copy to `plugins/` directory
5. Restart application

### plugin.yaml

```yaml
name: my-plugin
version: 1.0.0
description: My custom plugin
main: my_plugin.py
requirements:
  - requests>=2.28
```
