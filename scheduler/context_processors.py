from django.db.models import Q
from .models import Workspace, WorkspaceMember

def workspace_context(request):
    """
    Context processor providing active workspace, role permissions,
    and workspace list to all templates.
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {
            'active_workspace': None,
            'user_role': None,
            'is_workspace_admin': False,
            'is_workspace_owner': False,
            'can_manage_content': False,
            'user_workspaces': [],
        }

    user = request.user
    active_ws = None
    active_ws_id = request.session.get('active_workspace_id')

    if active_ws_id:
        active_ws = Workspace.objects.filter(
            id=active_ws_id
        ).filter(
            Q(owner=user) | Q(memberships__user=user)
        ).first()

    if not active_ws:
        # Fall back to first owned workspace, then first member workspace
        active_ws = Workspace.objects.filter(owner=user).first()
        if not active_ws:
            active_ws = Workspace.objects.filter(memberships__user=user).first()

    # If user has no workspace at all, auto-create personal default workspace
    if not active_ws:
        display_name = user.first_name.strip() if user.first_name else user.username
        active_ws = Workspace.objects.create(
            name=f"{display_name}'s Workspace",
            owner=user,
            timezone='Asia/Kolkata'
        )
        WorkspaceMember.objects.get_or_create(
            workspace=active_ws,
            user=user,
            defaults={'role': 'OWNER'}
        )

    # Store resolved active workspace id in session
    request.session['active_workspace_id'] = active_ws.id

    # Determine user's role in active workspace
    user_role = active_ws.get_user_role(user)

    # All workspaces accessible by user
    user_workspaces = Workspace.objects.filter(
        Q(owner=user) | Q(memberships__user=user)
    ).distinct().order_by('-created_at')

    return {
        'active_workspace': active_ws,
        'user_role': user_role,
        'is_workspace_admin': user_role in ('OWNER', 'ADMIN'),
        'is_workspace_owner': user_role == 'OWNER',
        'can_manage_content': user_role in ('OWNER', 'ADMIN', 'EDITOR'),
        'user_workspaces': user_workspaces,
    }
