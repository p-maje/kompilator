<a href="README.md">EN</a> | PL

# Projekt kompilatora
Kompilator prostego języka imperatywnego stworzony podczas kursu Języki formalne i techniki translacji na WPPT, PWr (semestr
zimowy 20/21).

## Technologie
- **Python 3.8.5**  
- **<a href=https://pypi.org/project/sly/>SLY 0.4</a>**

## Użycie
```bash
python3 compiler.py <nazwa pliku wejściowego> <nazwa pliku wyjściowego>
```

## Pliki
- `specs.pdf` – zawiera wymagania dotyczące projektu, gramatykę kompilowanego języka i obsługiwane komendy języka wyjściowego,
- `compiler.py` – zawiera lekser i parser oraz skrypt czytający plik wejściowy i wypisujący kod do pliku wyjściowego,  
- `symbol_table.py` – zawiera klasy odpowiedzialne za zarządzanie zmiennymi i pamięcią,  
- `code_generator.py` – zawiera klasę generującą kod assemblera na podstawie drzewa skonstruowanego przez parser.
### Dodatkowo
- W katalogach z testami umieszczone są przykładowe programy pozwalające na sprawdzenie poprawności generowanego kodu. Autorami większości z nich są <a href="https://www.cs.pwr.edu.pl/gotfryd">mgr inż. Karol Gotfryd</a> i <a href="https://www.cs.pwr.edu.pl/gebala">dr Maciej Gębala</a>. Można je uruchomić z użyciem skryptu `test.sh`, jako argument wywołania podając wybrany katalog. Testy sprawdzające obsługę błędów można uruchomić z użyciem skryptu `test_errors.sh` bez argumentów wywołania. Skrypty należy wykonywać z katalogu, w którym znajdują się pliki projektu; wymagają też skompilowanej maszyny wirtualnej w tym samym katalogu.
- W katalogu `virtual_machine` znajduje się kod maszyny wirtualnej autorstwa dra Macieja Gębali. Sporo testów wymaga skompilowania jej w wariancie z <a href="https://www.ginac.de/CLN/">biblioteką CLN</a>.
- W katalogu `misc` znajdują się dodatkowe pomocnicze skrypty.

## Uwagi i rady po projekcie
Kompilator przeszedł wszystkie testy rankingowe i zajął ostatecznie 13 miejsce. Zastosowane w nim optymalizacje są dosyć
proste i lokalne, ale jak widać całkiem skuteczne (szczególnie duże znaczenie mają pewnie uproszczenia operacji 
arytmetycznych i całkiem okej napisane pętle). Optymalizacja rejestrów okazała się skomplikowana (głównie ze względu na 
sposób odczytu i zapisu pamięci w zadanym assemblerze), dlatego w końcu z niej zrezygnowałem, więc generowany kod zawiera 
bardzo dużo niepotrzebnych loadów i store'ów. Nie udało mi się też doprowadzić do końca optymalizacji związanych z 
usuwaniem martwego kodu.  
  
Próby implementowania tych potężniejszych optymalizacji znajdują się na branchach i bazują na książce *Kompilatory: 
reguły, metody i narzędzia* – Aho, Lam, Sethi, Ullman. W przypadku decydowania się na takie radykalne metody warto 
napisać kompilator tak, żeby zawierał etap generowania kodu pośredniego, na którym łatwiej jest przeprowadzać tego 
typu optymalizacje. Wersja ostateczna projektu nie ma w sobie tego etapu, występuje on natomiast na branchu `dead_code`.  
  
Jeśli chodzi o kolejność prac, warto zacząć od leksera i parsera, potem podstawowej wersji tablicy symboli. Trzeba 
zdecydować o strukturze danych, z których generowany będzie kod assemblera. Ja wybrałem proste syntax tree 
reprezentowane przez zagnieżdżone krotki, inną opcją jest wspomniany wcześniej kod pośredni (przykłady w rozdziale 6 
*Kompilatorów*). W generowaniu kodu assemblera dobrze będzie wziąć się najpierw za prostsze sprawy – generowanie stałych
i instrukcje wejścia/wyjścia. Potem operacje arytmetyczne, instrukcje warunkowe, na koniec pętle, które z nich korzystają. 
Obsługę większości błędów (tych niewykrywalnych w fazie parsowania) można raczej zostawić sobie na koniec. 
Będzie okej, trzymam kciuki.