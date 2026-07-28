* OpenStatSpec SPSS SAV/ZSAV 1.0 conformance-fixture generator.
*
* Before running: create C:\OpenStatSpec-fixtures\ or replace that directory
* in every GET FILE and SAVE OUTFILE command below.  No SPSS macro is used.
* The generated data is synthetic and intended for CC0 publication.

SET UNICODE=ON.

* -------------------------------------------------------------------------.
* core-numeric-string.sav.
* -------------------------------------------------------------------------.
DATA LIST FREE /
  id (F3.0)
  score (F10.4)
  text_value (A40).
BEGIN DATA
1 1.5 "alpha"
2 -12345.6789 "not_blank_yet"
3 . "trailing spaces   "
4 0 "München"
END DATA.
IF id = 2 text_value = ''.
VARIABLE LABELS
  id 'Synthetic case identifier'
  score 'Binary64-oriented numeric test value'
  text_value 'Short text; blank is an ordinary value'.
VARIABLE LEVEL id (NOMINAL) score (SCALE) text_value (NOMINAL).
SAVE OUTFILE='C:\OpenStatSpec-fixtures\core-numeric-string.sav'.
EXECUTE.

* -------------------------------------------------------------------------.
* dictionary-and-display.sav.
* -------------------------------------------------------------------------.
DATA LIST FREE /
  respondent_id (F4.0)
  gender (F1.0)
  satisfaction (F1.0)
  income (F10.2)
  comment (A80).
BEGIN DATA
1001 1 4 1234.50 "First response"
1002 2 2 98.75 "Second response"
END DATA.
COMPUTE interview_date = DATE.DMY(15,1,2024).
IF respondent_id = 1002 interview_date = DATE.DMY(16,1,2024).
FILE LABEL 'OpenStatSpec synthetic dictionary and display fixture'.
ADD DOCUMENT
  "First ordered document line."
  "Second ordered document line.".
VARIABLE LABELS
  respondent_id 'Respondent identifier'
  gender 'Self-reported gender'
  satisfaction 'Overall satisfaction'
  interview_date 'Date of interview'
  income 'Reported monthly income'
  comment 'Free-text comment'.
VALUE LABELS
  gender 1 'Woman' 2 'Man' 9 'Not stated'
 /satisfaction 1 'Very dissatisfied' 2 'Dissatisfied' 3 'Neutral'
               4 'Satisfied' 5 'Very satisfied'.
FORMATS respondent_id (F8.0) gender (F2.0) satisfaction (F2.0)
  interview_date (ADATE10) income (DOLLAR12.2) comment (A80).
VARIABLE LEVEL gender (NOMINAL) satisfaction (ORDINAL)
  income (SCALE) comment (NOMINAL).
VARIABLE ROLE
 /NONE respondent_id comment
 /INPUT gender interview_date income
 /TARGET satisfaction.
VARIABLE WIDTH respondent_id (8) gender (8) satisfaction (10) comment (40).
VARIABLE ALIGNMENT respondent_id (RIGHT) gender (CENTER) satisfaction (CENTER)
  comment (LEFT).
SAVE OUTFILE='C:\OpenStatSpec-fixtures\dictionary-and-display.sav'.
EXECUTE.

* -------------------------------------------------------------------------.
* missing-rules.sav.
* -------------------------------------------------------------------------.
DATA LIST FREE /
  discrete_numeric (F3.0)
  discrete_string (A12)
  ranged_missing (F4.0)
  range_plus_code (F4.0)
  lowest_to_zero (F8.2)
  highest_from_100 (F8.2).
BEGIN DATA
1 "valid" 10 10 2 99
97 "REFUSED" 97 97 -1 100
98 "NOANSWER" 99 999 0 101
99 "" 100 9999 -99999 99999
END DATA.
MISSING VALUES
  discrete_numeric (97, 98, 99)
 /discrete_string ('REFUSED', 'NOANSWER')
 /ranged_missing (97 THRU 99)
 /range_plus_code (97 THRU 99, 9999)
 /lowest_to_zero (LOWEST THRU 0)
 /highest_from_100 (100 THRU HIGHEST).
SAVE OUTFILE='C:\OpenStatSpec-fixtures\missing-rules.sav'.
EXECUTE.

* -------------------------------------------------------------------------.
* long-utf8-and-attributes.sav.
* -------------------------------------------------------------------------.
DATA LIST FREE /
  short_text (A80)
  long_utf8_text (A512).
BEGIN DATA
"Tere" "Pikk UTF-8 tekst: õäöü ÕÄÖÜ — 日本語 — Ελληνικά. See väärtus on tahtlikult üle 255 baidi ja jätkub kordusega: õäöü ÕÄÖÜ 日本語 Ελληνικά õäöü ÕÄÖÜ 日本語 Ελληνικά õäöü ÕÄÖÜ 日本語 Ελληνικά õäöü ÕÄÖÜ 日本語 Ελληνικά õäöü ÕÄÖÜ 日本語 Ελληνικά õäöü ÕÄÖÜ 日本語 Ελληνικά õäöü ÕÄÖÜ 日本語 Ελληνικά õäöü ÕÄÖÜ 日本語 Ελληνικά."
END DATA.
VARIABLE LABELS long_utf8_text 'Long UTF-8 string value exceeding 255 bytes'.
VARIABLE ATTRIBUTE VARIABLES=long_utf8_text
  ATTRIBUTE=source_tags[1]('synthetic')
            source_tags[2]('utf8')
            source_tags[3]('long-string').
DATAFILE ATTRIBUTE
  ATTRIBUTE=fixture_metadata[1]('OpenStatSpec')
            fixture_metadata[2]('1.0')
            fixture_metadata[3]('synthetic').
SAVE OUTFILE='C:\OpenStatSpec-fixtures\long-utf8-and-attributes.sav'.
EXECUTE.

* -------------------------------------------------------------------------.
* sets-source.sav. Define Variable Sets manually after this script completes.
* -------------------------------------------------------------------------.
DATA LIST FREE /
  respondent_id (F4.0)
  age (F3.0)
  gender (F1.0)
  channel_email (F1.0)
  channel_sms (F1.0)
  channel_web (F1.0)
  preferred_contact_1 (F1.0)
  preferred_contact_2 (F1.0).
BEGIN DATA
1 32 1 1 0 1 1 3
2 45 2 0 1 0 2 1
END DATA.
MRSETS
 /MDGROUP NAME=$contact_modes LABEL='Contact modes (multiple)'
   CATEGORYLABELS=VARLABELS
   VARIABLES=channel_email channel_sms channel_web VALUE=1
 /MCGROUP NAME=$preferred_contact LABEL='Preferred contact mode'
   VARIABLES=preferred_contact_1 preferred_contact_2.
VALUE LABELS preferred_contact_1 preferred_contact_2 1 'Email' 2 'SMS' 3 'Web'.
SAVE OUTFILE='C:\OpenStatSpec-fixtures\sets-source.sav'.
EXECUTE.

* -------------------------------------------------------------------------.
* zsav-compressed.zsav: real ZLIB-compressed SPSS system file.
* -------------------------------------------------------------------------.
GET FILE='C:\OpenStatSpec-fixtures\dictionary-and-display.sav'.
SAVE OUTFILE='C:\OpenStatSpec-fixtures\zsav-compressed.zsav' /ZCOMPRESSED.
EXECUTE.

* The preflight-too-wide fixture is SQL-profile-specific. Generate it later
* in the conformance runner with one more variable than that profile permits.
