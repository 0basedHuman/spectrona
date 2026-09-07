from .config_file import (
    _chmod_user_only,
    config_path,
    default_config_text,
    default_policy_text,
    ensure_gateway_auth_token,
    policy_path,
    spectrona_home,
)


def run(force: bool = False) -> int:
    home = spectrona_home()
    path = config_path()
    policy = policy_path()
    home.mkdir(parents=True, exist_ok=True)
    (home / "logs").mkdir(parents=True, exist_ok=True)

    if path.exists() and not force:
        print(f"Spectrona config already exists: {path}")
        print("Use --force to rewrite it.")
        if ensure_gateway_auth_token(path):
            print("Added gateway auth token to existing config.")
        if not policy.exists():
            policy.parent.mkdir(parents=True, exist_ok=True)
            policy.write_text(default_policy_text())
            print(f"Wrote Spectrona policy: {policy}")
        return 0

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(default_config_text())
    _chmod_user_only(path)
    policy.parent.mkdir(parents=True, exist_ok=True)
    if force or not policy.exists():
        policy.write_text(default_policy_text())
    print(f"Wrote Spectrona config: {path}")
    print(f"Wrote Spectrona policy: {policy}")
    print(f"Logs directory: {home / 'logs'}")
    return 0
