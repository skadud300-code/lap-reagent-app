#!/bin/bash
SRC=""
if [ -f "$HOME/Downloads/reagent-manager.html" ]; then
    SRC="$HOME/Downloads/reagent-manager.html"
elif [ -f "$HOME/Downloads/reagent-manager (1).html" ]; then
    SRC="$HOME/Downloads/reagent-manager (1).html"
fi

if [ -z "$SRC" ]; then
    echo "FILE NOT FOUND: reagent-manager.html"
    exit 1
fi

cp "$SRC" "$HOME/reagent/public/index.html"
echo "복사 완료"

if [ -f "$HOME/Downloads/sw.js" ]; then
    cp "$HOME/Downloads/sw.js" "$HOME/reagent/public/sw.js"
fi

cd "$HOME/reagent"
firebase use lap-reagent-app
firebase deploy --only hosting
echo "DONE: https://lap-reagent-app.web.app"
