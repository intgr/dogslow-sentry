#!/usr/bin/env bash
set -ex

if [[ -n "$(git status -s)" ]]; then
  echo "git working tree is not clean, aborting"
  exit 1
fi
if [[ "$VIRTUAL_ENV" == ""  ]]; then
  echo "this script must be executed inside an active virtual env, aborting"
  exit 1
fi

pip install --upgrade pip setuptools wheel twine build
rm -rf dist/ build/
python -m build
twine upload dist/*
