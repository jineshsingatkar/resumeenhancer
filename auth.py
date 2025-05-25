from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import current_user


def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if not current_user.is_admin:
            flash('Admin access required.', 'error')
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def subscription_required(subscription_types):
    """Decorator to require specific subscription types"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this feature.', 'warning')
                return redirect(url_for('login'))
            if current_user.subscription_type not in subscription_types:
                flash('Premium subscription required for this feature.', 'warning')
                return redirect(url_for('pricing'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator