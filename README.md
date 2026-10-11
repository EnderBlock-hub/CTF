# CTF writeups

Разборы заданий с CTF-соревнований. По каждому заданию описан ход анализа, сама уязвимость и шаги, которыми решение воспроизводится. Флаги намеренно не публикуются.

## FortID CTF 2026

### Web

| Задание | Техника |
|---|---|
| [Do You Know Lika?](FortID/Web/01-do-you-know-lika/README.md) | Server-side template injection в Handlebars через prototype pollution |
| [Ultimative PHP](FortID/Web/02-ultimative-php/README.md) | Обход проверок PHP: мэнглинг имён параметров, коллизия `Array`, magic hash, object injection |
| [Doctor Bye Bye](FortID/Web/03-doctor-bye-bye/README.md) | Blind SQL injection через `ORDER BY` на основе boolean-оракула |

### Cryptography

| Задание | Техника |
|---|---|
| [DESBox](FortID/Cryptography/01-desbox/README.md) | Свойство дополнения 3DES в обход проверок ключей |

### OSINT

| Задание | Техника |
|---|---|
| [Baby OSINT](FortID/OSINT/01-baby-osint/README.md) | Восстановление события по фотографии и перекрёстный поиск |

## Как устроен репозиторий

Каждый разбор лежит по пути `FortID/<категория>/<задание>/`. Внутри папки:

- `README.md` - сам разбор с объяснением и шагами;
- исходник задания, когда он помогает понять уязвимость;
- готовый скрипт решения, если он нужен.
