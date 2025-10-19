# Check Renovate configuration
check-renovate:
    npx --yes --package renovate@latest -- renovate-config-validator --strict

tox:
    uv run tox
