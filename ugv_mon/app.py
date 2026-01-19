"""
UGV-MON Dash Application Module.

Creates and configures the Dash application instance with:
- External stylesheets (Inter font)
- Layout initialization
- Callback registration

This module provides the app factory pattern for flexible deployment.
"""

import dash

from .layouts.main_layout import create_main_layout
from .callbacks.update_callbacks import register_callbacks, get_data_generator
from .config import config


def create_app() -> dash.Dash:
    """
    Create and configure the Dash application.
    
    This factory function creates a new Dash app instance with:
    - Configured external stylesheets
    - Suppressed callback exceptions (for pattern-matching callbacks)
    - Initial layout with mock data
    - Registered callbacks
    
    Returns:
        Configured Dash application instance
        
    Usage:
        >>> app = create_app()
        >>> app.run_server(debug=True)
    """
    # Create Dash app (no external stylesheets - internal network only)
    app = dash.Dash(
        __name__,
        suppress_callback_exceptions=True,
        title=config.app.name,
    )
    
    # Initialize data generator and get initial data
    data_gen = get_data_generator()
    initial_data = data_gen.generate_initial_data()
    initial_logs = data_gen.get_logs(limit=50)
    
    # Set layout
    app.layout = create_main_layout(initial_data, initial_logs)
    
    # Register callbacks
    register_callbacks(app)
    
    return app


# Module-level app instance for imports
app = create_app()
