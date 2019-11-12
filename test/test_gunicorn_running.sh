set -e

echo "Registry"
curl --fail http://localhost:8080/v1/_internal_ping
echo ""

echo "Verbs"
curl --fail http://localhost:8080/c1/_internal_ping
echo ""

echo "Security scan"
curl --fail http://localhost:8080/secscan/_internal_ping
echo ""

echo "Web"
curl --fail http://localhost:8080/_internal_ping
echo ""
