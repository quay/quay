#!/bin/bash

# File names should be seprated by pipe(|). Eg: 'file1|file2|file3'
MUST_NOT_CHANGE='local-dev/stack/config.yaml'

if git diff --name-only --cached --diff-filter=ACMR |
   grep -E "$MUST_NOT_CHANGE"
then
  echo Commit would modify one or more files that must not change. Please remove them before commiting. \
       If you\'d still like to commit, please use '--no-verify'
  exit 1
else
  exit 0
fi
