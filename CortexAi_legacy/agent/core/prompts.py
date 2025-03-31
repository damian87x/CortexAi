from typing import List, Dict, Optional

class Prompt:
    """
    A flexible prompt container that holds a list of role/content messages.
    Useful for chat-based LLMs (like GPT-3.5-turbo/4) or text-based models.

    Methods:
      - add_message(role, content)
      - to_messages() -> List of {role, content}
      - to_text() -> single string
    """

    def __init__(self):
        self.messages = []

    def add_message(self, role: str, content: str) -> None:
        """Add a message with specified role and content"""
        self.messages.append({"role": role, "content": content})

    def add_system_message(self, content: str) -> None:
        """Convenience method to add a system message"""
        self.add_message("system", content)

    def add_user_message(self, content: str) -> None:
        """Convenience method to add a user message"""
        self.add_message("user", content)

    def add_assistant_message(self, content: str) -> None:
        """Convenience method to add an assistant message"""
        self.add_message("assistant", content)

    def to_messages(self) -> List[Dict[str, str]]:
        """Return messages in a format suitable for chat models"""
        return self.messages

    def to_text(self) -> str:
        """
        Convert messages to a single text string.
        Useful for text completion models that don't support chat format.
        """
        lines = []
        for msg in self.messages:
            role = msg["role"].capitalize()
            content = msg["content"]
            lines.append(f"{role}:\n{content}\n")
        return "\n".join(lines)

    def clear(self) -> None:
        """Remove all messages"""
        self.messages = []

    def __len__(self) -> int:
        """Return the number of messages"""
        return len(self.messages)


class PromptTemplate:
    """
    A template for creating prompts with placeholders.

    Usage:
        template = PromptTemplate("Hello, {name}! The weather is {weather}.")
        prompt = template.format(name="Alice", weather="sunny")
    """

    def __init__(self, template: str):
        self.template = template

    def format(self, **kwargs) -> str:
        """
        Fill in placeholders with provided values.

        Args:
            **kwargs: Key-value pairs where keys match placeholders in the template

        Returns:
            Formatted string with placeholders replaced
        """
        return self.template.format(**kwargs)


class MultiRolePromptTemplate:
    """
    A more advanced template for creating multi-role prompts with placeholders.

    Usage:
        template = MultiRolePromptTemplate()
        template.add_template("system", "You are an assistant helping with {task}.")
        template.add_template("user", "Help me with {request}.")
        prompt = template.format(task="coding", request="Python functions")
    """

    def __init__(self):
        self.templates = []

    def add_template(self, role: str, template: str) -> None:
        """Add a template for a specific role"""
        self.templates.append({"role": role, "template": template})

    def format(self, **kwargs) -> Prompt:
        """
        Fill in placeholders in all templates and return a Prompt object.

        Args:
            **kwargs: Key-value pairs for all placeholders in templates

        Returns:
            A populated Prompt object
        """
        prompt = Prompt()
        for template in self.templates:
            try:
                content = template["template"].format(**kwargs)
                prompt.add_message(template["role"], content)
            except KeyError as e:
                prompt.add_message(
                    template["role"],
                    f"ERROR: Missing placeholder {e} in template: {template['template']}"
                )
        return prompt
