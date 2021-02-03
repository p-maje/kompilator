for f in $(find ./testy_gotfryd -type f -name "error*.imp") ; do
    echo -e "\n$f"
    sed "/]/q" $f
    python3 compiler.py $f out.mr && ./maszyna-wirtualna out.mr
done
