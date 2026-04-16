\ Troll has no module/import system, so shared helpers are duplicated here.
\ MODE selects which top-level helper to evaluate:
\ 1 eldritchblast
\ 2 eldritchblastaction
\ 3 guidingbolt
\ 4 inflictwounds
\ 5 fireball
\ 6 sacredflame
\ 7 magicmissile
\ SCALE optionally rescales final outcomes for cross-language comparison.

function hit(ac, bonus) =
  (d20 + bonus) >= ac

function damageonhit(ac, bonus, dmg) =
  if call hit(ac, bonus) then dmg else 0

function savefail(dc, savebonus) =
  (d20 + savebonus) < dc

function savehalf(dc, savebonus, dmg) =
  if call savefail(dc, savebonus) then dmg else dmg / 2

function eldritchblast(ac, bonus, cha) =
  call damageonhit(ac, bonus, d10 + cha)

function eldritchblastaction(beams, ac, bonus, cha) =
  sum (beams # (call eldritchblast(ac, bonus, cha)))

function guidingbolt(ac, bonus) =
  call damageonhit(ac, bonus, sum 4d6)

function inflictwounds(ac, bonus) =
  call damageonhit(ac, bonus, sum 3d10)

function fireball(dc, savebonus) =
  call savehalf(dc, savebonus, sum 8d6)

function sacredflame(dc, savebonus) =
  if call savefail(dc, savebonus) then sum 2d8 else 0

function magicmissile(darts) =
  sum (darts d4) + darts

function runspell(mode, ac, bonus, stat, amount, dc, savebonus, scale) =
  if mode = 1 then scale * call eldritchblast(ac, bonus, stat)
  else if mode = 2 then scale * call eldritchblastaction(amount, ac, bonus, stat)
  else if mode = 3 then scale * call guidingbolt(ac, bonus)
  else if mode = 4 then scale * call inflictwounds(ac, bonus)
  else if mode = 5 then scale * call fireball(dc, savebonus)
  else if mode = 6 then scale * call sacredflame(dc, savebonus)
  else scale * call magicmissile(amount)

call runspell(MODE, AC, BONUS, STAT, COUNT, DC, SAVEBONUS, SCALE)
