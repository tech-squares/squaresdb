#!/bin/sh

set -euf

settings=$(dirname "$0")
base="$settings/../.."

# TODO: make this actually work. Really, port to Python with "real" templating.
if [ -v EMAIL ] && [ -n "$EMAIL" ]; then
    email="$EMAIL"
else
    read -p "Enter your email address: " email
fi

echo Creating config files...
secret=$(python -c "import random; print(''.join([random.choice('abcdefghijklmnopqrstuvwxyz0123456789@#%-_=+') for i in range(50)]))")
secret_re="s/^#SECRET_KEY = something$/SECRET_KEY = '$secret'/"
forced_re="s/'squares-db-forced-recipient@mit.edu'/'$email'/"
sed -e "$secret_re" -e "$forced_re" < "$settings/local.dev-template.py" > "$settings/local.py"
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
echo "- Create a superuser account:"
echo "  ../manage.py createsuperuser --email $email --username $USER"
