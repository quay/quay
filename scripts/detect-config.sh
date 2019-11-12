if find . -name "config.yaml" -exec false {} +
then
  exit 0
else
  echo '!!! config.yaml found in container !!!'
  find . -name "config.yaml"
  exit -1
fi