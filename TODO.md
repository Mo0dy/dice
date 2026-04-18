# TODOS
- `total` should also accept unnamed axis
- Distributions should not include fields with probability 0 in rendering?.
- Have high precision rationals (need to be enabled)
- Add functionality for comparing distributions (divergences and equality)

## Brainstorming on Configurations
- Attack configuration likely wants a first-class unresolved `AttackSpec`-style value plus transform helpers, not just default kwargs.
- Reuse the existing `$` operator for left-to-right attack configuration instead of adding a separate pipe syntax.
- Sketch:
  `longsword(base_bonus, mod) $ with_advantage $ with_bless $ with_hunters_mark $ resolve_attack(ac)`
- Semantics:
  constructors produce an attack description, modifier helpers rewrite that description, and only `resolve_attack(...)` turns it into a distribution.
- This would avoid helper-name combinatorics such as `attack_damage_adv_bless`, `bless_longsword`, `rapier_sneak_attack_adv`, etc.
- Open design question:
  decide whether this needs records/structs, tagged runtime values, or some narrower first-class config object dedicated to combat helpers.

## README.md update
- Split language documentation into two stages:
  1. Minimal ttrpg calculations. The things everyone needs explained with tabletop syntax
  +rendering the outcomes.
  2. Introducing additional language features, still mostly using ttrpg logic.
  3. Full documentation. Replace ttrpg language with probability theory for exact statements but always also explain what this means practically. Document all language features here.
- **At every point of the documentation highlight stochastical and language pitfalls**. Such as 2d6 != 2 * d6 but d6^2.
- This becomes very important for the split operator.
- 1. and 2. should live in the README.md. We should have a separate documentation system for 3.
- Lean heaviliy into using examples for 1. and 2.

### Documentation system
- Keep `README.md` as the quickstart and stage 1 / 2 documentation for GitHub readers.
- Add a separate canonical user-facing language manual in this repository, outside the current internal `docs/` area.
- Prefer a Markdown-native static docs system such as MkDocs for the manual.
- Treat this repository as the single source of truth for language documentation.
- Serve the built language manual from this repository, ideally via GitHub Pages.
- Treat `dice-web` as a consumer of the canonical docs, not a second source of truth. Link to the manual from `dice-web` or import the built static site there, but do not maintain a separate copy.
- Add executable testing for fenced `dice` examples in the full manual, similar to the current `README.md` example coverage.
- Each major language reference page should explain practical intuition, exact semantics, pitfalls, and executable examples.
- Once this is implemented, update `AGENTS.md` and the files under `docs/` so they explain where the user-facing documentation lives, which documentation is canonical, and how it is built and served in this repository.

### README.md content
- Begin with very brief introduction (1-2 sentences. Note that the web-version is an unfinished demo for testing only and that the local version is more mature. Also mention that this is easily extensible with python and link to the correct section in the readme.) and links to `web-version` `installation` `usage` `api-docs` `examples`. Then recommend to read the beginning of this readme to get started. 
- The most important things about dice are: Easy to use but powerful while staying mostly readable. Great python interop for extension. Easy parameter studies anywhere in the language. (Give some first examples here?)
    - Also note AnyDice and Troll as inspiration. And note that troll is used for parity testing.
- Immediately continue with the most impactful examples (1.) for basic ttrpg calculations.
- Continue with (2.) by giving a brief overview over the things explained in this section. Mainly function definitions / variables / sweeps / imports and a better explanation of split and some basic stochastic operations and why they are interesting. 
Also gives an overview over extension with python (this is the first place we explaint he types of dice, since it is important to know them when writing python bindings. Though the first python example should not use types (I think we support this?)). This has two parts: How to extend the language with custom python library modules and how to call the language from python for more advanced postprocessing / operations. 
End with a list of all language features similar to what we have now) and a link to the `api-docs`
- Next is the installation section.
- Finally Section on Running dice with cli arguments / settings etc. (most cli arguments can also be set in a dice program).
- Have a section on similar projects. Simply name them and give a sentence about them (take that from their own documentation and quote it).

### Interesting content that should be documented somewhere (as an exmple mostly)
- I think it is possible to redefine library functions simply by overwriting them. Then all functions we call use the new definition.
- E.g. if we want to modify `save_success` to respect nat 1 and 20 we can simply redefine `save_sucess_with_roll`.


### Add more parameter study examples. Also perhaps use boolean parameters for activate bless / deactivate bless.


# Improving Rendering Comments
/home/felix/_Documents/Projects/dice/samples/dnd/ability_scores_4d6h3.dice
- For the "Total modifier sum across 6 scores" plot it would be nice to immediately zoom into the central part without showing the whole tail (left and right). (This would however need some indication that we have cliped the tail. We can safely clip a tail if its total probability mass is less than 0.1%). Then perhaps insert a comment in the plot.

/home/felix/_Documents/Projects/dice/samples/dnd/agonizing_eldritch_blast_vs_ac.dice
- Add a second plot that shows how much additional damage Agonizing / Hex + Agonizing make over AC

/home/felix/_Documents/Projects/dice/samples/dnd/combat_profiles.dice
- Since this is a damage comparison It's a bit annoying that we include the miss chance explicitly in the plot. It might be nice to remove this by default (if it is a lot higher than the other probabilities) and instead add it as text somewhere.
- I love the plot that is chosen. The "stepped" lines are a great in between of bar plots and line plots.

/home/felix/_Documents/Projects/dice/samples/dnd/eldritch_blast_debug.dice
- Add another full width plot below the hero plot that shows damage comparison between single double and three beams.
- The three damage distributions have the problem with the miss change dominating the y-scale again. 

/home/felix/_Documents/Projects/dice/samples/dnd/strategy_heatmap.dice
- Add a comparison plot over ac.
- The margin plot should be placed below the best stragety heatmap and I don't think it should probably not be a contour plot but a normal one instead.

/home/felix/_Documents/Projects/dice/samples/dnd/fireball_party_total.dice
- There is no dense distribution. It plots value over spell slots

/home/felix/_Documents/Projects/dice/samples/dnd/magic_missile_vs_slot.dice
- Should have y axis label "dmg"

/home/felix/_Documents/Projects/dice/samples/dnd/martial_tradeoffs.dice
- Same as for stragegy_heatmap.
- Also should include two plots. One "best" plot and one plot with the damage.

/home/felix/_Documents/Projects/dice/samples/dnd/spell_slot_showdown.dice
- Same as above

# Evaluate Python / report interop (it should be easy to modify existing rendered reports / the report spec based rendering from python).
# Improved Examples
- Add comments to samples
- Create sample files that teach the language / reporting etc.
