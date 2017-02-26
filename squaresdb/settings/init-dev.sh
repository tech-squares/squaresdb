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
echo
echo Creating initial revisions...
$base/manage.py createinitialrevisions --comment='Initial revision (in setup script)' membership

echo; echo
echo Done! Run the server with
echo ./manage.py runserver 8007
echo or similar

echo
echo "Possible next steps:"
echo "- Clone the membership database (on Athena: /mit/tech-squares/club-private/signin/git/) and import it:"
echo "  membership/parsedb.py csv2django --csv membership/club-db/club.csv"
echo "- Create a superuser account (update email/username appropriately):"
echo "  ../manage.py createsuperuser --email $USER@example.com --username $USER"
