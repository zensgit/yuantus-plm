import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from yuantus.meta_engine.business_logic.models import Method, MethodType

logger = logging.getLogger(__name__)


class MethodService:
    def __init__(self, session: Session):
        self.session = session

    def execute_method(self, method_name: str, context: Dict[str, Any]) -> Any:
        """
        Execute a server method by name.

        Args:
            method_name: Name of the Method record in DB.
            context: Dictionary of objects to inject into the execution scope.
                     Expected keys: 'item', 'session', 'user_id', 'plm', etc.

        Returns:
            The return value of the script (if any), or modifies context objects in place.
        """
        method = self.session.query(Method).filter_by(name=method_name).first()
        if not method:
            logger.error(f"Method '{method_name}' not found.")
            raise ValueError(f"Method '{method_name}' not found.")

        if method.type == MethodType.PYTHON_SCRIPT or method.type == "python_script":
            return self._execute_script(method, context)
        elif method.type == MethodType.PYTHON_MODULE or method.type == "python_module":
            return self._execute_module(method, context)
        else:
            raise ValueError(f"Unknown Method Type: {method.type}")

    def _execute_script(self, method: Method, context: Dict[str, Any]) -> Any:
        """
        Execute raw Python code stored in database.

        Security Note: This uses exec(). In production, this must be sandboxed.
        For this prototype, we assume trusted admin access.
        """
        code = method.content
        if not code:
            return None

        # Prepare Global Scope
        # We inject everything in 'context' into the local scope
        local_scope = context.copy()

        # Add common utilities
        local_scope["logger"] = logger

        try:
            # We wrap the code in a function to allow 'return' statements if needed,
            # OR we just exec it. Aras style: Code is the body of a function.
            # Let's assume the code IS the body.
            # But simple exec() doesn't return value easily unless assigned to a variable.
            # Better approach: The user code should define a "main()" function or just run.

            # Implementation Choice: Code is executed as a script.
            # If it sets a variable 'result', we return it.

            exec(code, {}, local_scope)

            if "result" in local_scope:
                return local_scope["result"]
            return None

        except Exception as e:
            logger.error(f"Error executing method '{method.name}': {e}")
            raise e

    def _execute_module(self, method: Method, context: Dict[str, Any]) -> Any:
        """
        Load a Python function from a module path.
        Content format: "path.to.module:function_name"
        """
        import importlib

        content = method.content
        if ":" in content:
            mod_path, func_name = content.split(":")
        else:
            mod_path = content
            func_name = "main"

        try:
            mod = importlib.import_module(mod_path)
            func = getattr(mod, func_name)
            return func(**context)  # Pass context as kwargs? Or single context dict?
            # Aras passes specific args. Let's pass context dict for flexibility.
            # Or kwargs matching context keys.
        except Exception as e:
            logger.error(f"Error executing module '{method.name}': {e}")
            raise e
