#!/usr/bin/env python3

from copy import deepcopy

class Diceprop(object):
    """Holds a probability and has methods for modifiing."""

    def __init__(self, dicenum, dicesides):
        """Creates a standard dice probability."""
        self.distribution = self.rollprop(dicesides, dicenum)

    def __repr__(self):
        return str(self.distribution)

    def __str__(self):
        return self.__repr__()

    def rollprop(self, dicesides, dicenum):
        """Generate probability distribution for the roll of dicenum dice with dicesides sides"""
        # TODO: do proper maths! This is easy stuff!
        results = {0: 1}

        # add dicenum dice
        for _ in range(dicenum):
            # Dictionary to store next probability distribution
            results_new = {}
            # add every possible dice throw to every existing result
            for i in range(1, dicesides + 1):
                for value, prop in results.items():
                    new_value = value + i
                    new_prop = prop / dicesides

                    # add to new results
                    if new_value not in results_new:
                        results_new[new_value] = new_prop
                    else:
                        results_new[new_value] += new_prop
            results = results_new
        return results

    @staticmethod
    def add(left, right):
        """Can add two diceprops or one diceprop and one integer or two integers"""
        # swap so that left input will always be Diceprop
        if type(left) == int:
            # add two integers
            if type(right) == int:
                return left + right
            left, right = right, left

        if type(right) == int:
            # add constant to all dice values
            new_distrib = {}
            for dice, prop in left.distribution.items():
                new_distrib[dice + right] = prop
            # TODO: cleanup initializers
            retval = Diceprop(0, 0)
            retval.distribution = new_distrib
            return retval

        elif isinstance(right, Diceprop):
            # generate all new possibilities and assign random distribution
            new_distrib = {}
            for d1, p1 in left.distribution.items():
                for d2, p2 in right.distribution.items():
                    new_value = d1 + d2
                    new_prop = p1 * p2
                    if new_value in new_distrib:
                        new_distrib[new_value] += new_prop
                    else:
                        new_distrib[new_value] = new_prop
            # TODO: cleanup initializers
            retval = Diceprop(0, 0)
            retval.distribution = new_distrib
            return retval
        raise Exception("Can't add {} to Distribution!".format(right))

    @staticmethod
    def greaterorequal(left, right):
        if type(left) == int and type(right) == int:
            return left >= right

        # for now the left must be a distribution:
        # TODO: call lessthen and switch sides if left side is an integer
        if not isinstance(left, Diceprop):
            raise Exception("The left side of a comparison must be a Diceprop not {}".format(type(left)))

        if type(right) == int:
            won_changse = 0
            for dice, prop in left.distribution.items():
                if dice >= right:
                    won_changse += prop
            # HACK: this should probably return some basic probability object or something
            return {'True': won_changse, 'False': 1 - won_changse}
        else:
            # right is a distribution
            raise Exception("Not Implemented!")

if __name__ == "__main__":
    d1 = Diceprop(1, 2)
    print(d1)
    d2 = Diceprop(1, 2)
    print(d2)
    print(Diceprop.add(2, d1))
