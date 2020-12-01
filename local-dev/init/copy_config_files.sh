#! /bin/sh
QUAYPATH=${QUAYPATH:-"."}
QUAYCONF=${QUAYCONF:-"$QUAYPATH/conf"}

cd ${QUAYDIR:-"/"}


if [ -e $QUAYCONF/stack/robots.txt ]
then
  cp $QUAYCONF/stack/robots.txt $QUAYPATH/templates/robots.txt
fi

if [ -e $QUAYCONF/stack/favicon.ico ]
then
  cp $QUAYCONF/stack/favicon.ico $QUAYPATH/static/favicon.ico
fi