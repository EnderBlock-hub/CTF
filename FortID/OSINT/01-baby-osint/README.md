# Baby OSINT

| Field | Value |
|---|---|
| Platform | FortID CTF |
| Category | OSINT |
| Challenge file | [`handout.jpeg`](handout.jpeg) |
| Status | Solved |
| Flag | `FortID{hod...tsku:zeg...ge:wed...day:9...9}` (masked) |

## Challenge

![Challenge photograph](handout.jpeg)

The photograph shows a large public gathering in a city centre. The challenge asks four questions:

1. What was the exact name of the event in the photograph?
2. Which food festival was taking place in Zagreb on the same date, and whose organisers publicly supported the event?
3. Which day of the week had the highest average number of rides on the newly introduced public bicycles?
4. What was the largest number of those bicycles recorded at one location at the same time?

The flag format requires lowercase English letters, underscores instead of spaces, and no punctuation inside each answer.

## 1. Reading the photograph

The sign on the right contains the Croatian text `Pješačka zona`, meaning "pedestrian zone". The language, architecture, street furniture and dense central-city setting point to Croatia, and more specifically to Zagreb.

The most useful visual clue is the word `LIKA` on a placard in the crowd. Lika is a historical region of Croatia. That made it more productive to search for a Croatian public event connected with Lika than to search for a generic protest or festival in Zagreb.

The image itself does not provide a complete readable event title. It provides the location, language and one distinctive keyword, so the rest of the solve is an OSINT pivot from those clues.

## 2. Identifying the event

I searched combinations of `Lika`, `Zagreb`, `hodaj` and Croatian event terminology, then compared the results with the scene in the photograph. This led to **Hodaj za Liku, hodaj za Hrvatsku**, which translates roughly as "Walk for Lika, walk for Croatia".

The wording matches the clue on the placards and the scale of the gathering. The first answer is therefore the event's official name, normalised as one lowercase underscore-separated string.

Masked answer: `hod...tsku`

The important detail is to keep the Croatian spelling `Hrvatsku` before applying the flag normalisation. Translating the title into English would produce the wrong answer.

## 3. Finding the food festival

The second question is more specific than "what else happened in Zagreb?" It asks for a food festival held on the same date, nearby, whose organisers publicly supported the event from the photograph.

I followed the event coverage and checked the organisations mentioned around the date. Their publications connected the event with a Zagreb food festival. This cross-check matters because many festivals can match the city and date, while the organisers' public statement provides the identifying link required by the challenge.

Masked answer: `zeg...ge`

## 4. Determining the busiest weekday

The third clue points to Zagreb's public bicycle system. The challenge links a video of the mayor trying one of the newly introduced bicycles, which identifies the relevant system and time period.

I compared the available ride statistics by weekday instead of using a single daily total. The question asks for the largest **average** number of rides, so a raw record from one unusually busy day would not be enough. The highest average corresponds to one weekday.

Masked answer: `wed...day`

## 5. Counting bicycles at one location

The final question asks for a simultaneous location count, which is a different metric from total rides or the number of people attending an event. I checked the event-related bicycle report and used the number stated for the relevant snapshot.

There is a second, similar-looking peak value in another dataset, but it belongs to a different time window. Mixing the two gives a wrong, rejected flag, so I took the figure tied to this event and date.

Masked answer: `9...9`

## Result

All four values were confirmed from the photograph, Croatian event coverage and the bicycle statistics. The flag is kept masked below:

```text
FortID{hod...tsku:zeg...ge:wed...day:9...9}
```

## Sources

- [Prijatelji životinja - event coverage and the supporting festival](https://www.prijatelji-zivotinja.hr/index.hr.php?id=5285)
- [Index.hr - bicycle-related event figures](https://www.index.hr/fit/clanak/vise-od-900-ljudi-na-inmusic-doslo-bajsom/2805907.aspx)
- [Bajs - public bicycle event statistics](https://bajs.informacija.hr/events)

## Takeaways

The photograph supplied three useful pivots: Croatia, Zagreb and the word `LIKA`. The first answer came from matching those clues to a Croatian event name. The second required checking organiser statements, while the last two required reading the bicycle statistics carefully and distinguishing averages and time windows from superficially similar peak numbers.

