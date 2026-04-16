\ Troll has no module/import system, so these helpers are kept in one file.
\ MODE selects which top-level helper to evaluate:
\ 1 longswordattack
\ 2 greatweaponmaster
\ 3 recklessgreatweaponmaster
\ 4 rapiersneakattack
\ 5 blesslongsword
\ 6 critlongsword
\ 7 sharpshooter
\ 8 paladinsmite
\ 9 fighterattackaction
\ SCALE optionally rescales final outcomes for cross-language comparison.

function hit(ac, bonus) =
  (d20 + bonus) >= ac

function hitadv(ac, bonus) =
  ((max 2d20) + bonus) >= ac

function damageonhit(ac, bonus, dmg) =
  if call hit(ac, bonus) then dmg else 0

function damageonhitadv(ac, bonus, dmg) =
  if call hitadv(ac, bonus) then dmg else 0

function crithit(ac, bonus, hitdamage, critdamage) =
  roll := d20;
  if roll = 20 then critdamage
  else if (roll + bonus) >= ac then hitdamage
  else 0

function longswordattack(ac, bonus, abil) =
  call damageonhit(ac, bonus, d8 + abil)

function greatweaponmaster(ac, bonus, abil) =
  call damageonhit(ac, bonus - 5, sum 2d6 + abil + 10)

function recklessgreatweaponmaster(ac, bonus, abil) =
  call damageonhitadv(ac, bonus - 5, sum 2d6 + abil + 10)

function rapiersneakattack(ac, bonus, dex, sneakdice) =
  call damageonhit(ac, bonus, d8 + dex + sum (sneakdice d6))

function blesslongsword(ac, bonus, abil) =
  if ((d20 + d4) + bonus) >= ac then d8 + abil else 0

function critlongsword(ac, bonus, abil) =
  call crithit(ac, bonus, d8 + abil, sum 2d8 + abil)

function sharpshooter(ac, bonus, abil) =
  call damageonhit(ac, bonus - 5, d8 + abil + 10)

function paladinsmite(ac, bonus, abil, smitedice) =
  call crithit(ac, bonus,
               d8 + abil + sum (smitedice d8),
               sum 2d8 + abil + sum ((smitedice * 2) d8))

function fighterattackaction(attacks, ac, bonus, abil) =
  sum (attacks # (call longswordattack(ac, bonus, abil)))

function runweapon(mode, ac, bonus, abil, extra, attacks) =
  if mode = 1 then call longswordattack(ac, bonus, abil)
  else if mode = 2 then call greatweaponmaster(ac, bonus, abil)
  else if mode = 3 then call recklessgreatweaponmaster(ac, bonus, abil)
  else if mode = 4 then call rapiersneakattack(ac, bonus, abil, extra)
  else if mode = 5 then call blesslongsword(ac, bonus, abil)
  else if mode = 6 then call critlongsword(ac, bonus, abil)
  else if mode = 7 then call sharpshooter(ac, bonus, abil)
  else if mode = 8 then call paladinsmite(ac, bonus, abil, extra)
  else call fighterattackaction(attacks, ac, bonus, abil)

SCALE * call runweapon(MODE, AC, BONUS, MOD, EXTRA, ATTACKS)
