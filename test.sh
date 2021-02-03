for f in $(find $1 -type f -name "*.imp") ; do
    if [[ $f == *error* ]]; then
        echo "$f skipped."
        continue
    fi
    sed "/]/q" $f
    fname=$(basename $f .imp)
    dirname=${1%/}_out
    ./kompilator $f out.mr && ./maszyna-wirtualna out.mr ; read -p "Press enter to continue" || read -p "Press enter to continue"
done
