#!/bin/sh

set -euf

settings=$(dirname "$0")
base="$settings/../.."

echo Creating config files...
secret=$(python -c "import random; print(''.join([random.choice('abcdefghijklmnopqrstuvwxyz0123456789@#%-_=+') for i in range(50)]))")
secret_re="s/^#SECRET_KEY = something$/SECRET_KEY = '$secret'/"
sed -e "$secret_re" < "$settings/local.dev-template.py" > "$settings/local.py"
touch "$settings/local_after.py"

echo
echo Creating database and doing basic sync...
$base/manage.py migrate

echo; echo
echo Done! Run the server with
echo ./manage.py runserver 8007
echo or similar
