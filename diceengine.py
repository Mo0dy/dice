#!/usr/bin/env python3

"""The actual background processing of data"""


from copy import deepcopy


class ResultList(object):
    """Holds a dictionary of results for a comparison

    e.g. {10: 0.7, 11: 0.8}"""
   
    def __init__(self, result_list=[]):
        self.result_list = result_list

    def __repr__(self):
        return str(self.result_list)

class Distrib(object):
    """Holds a distribution. Is 0 initialized!!!

    example: {1: 0.5, 2: 0.5} for a d2
    """

    def __init__(self, distrib=None):
        # HACK: I don't get it but having distrib={} keyword argument is fucked up
        self.distrib = distrib if distrib else {}

    def __repr__(self):
        return str(self.distrib)

    def __getitem__(self, key):
        # returning 0 if no key is found makes adding easy
        if key in self.distrib:
            return self.distrib[key]
        else:
            return 0

    def __setitem__(self, key, value):
        self.distrib[key] = value

    def items(self):
        return self.distrib.items()


# There is also the normal python int
# And the normal python list

class Diceengine(object):
    """Wrapper for static objects that manipulate probabilites"""

    @staticmethod
    def exception(message):
        raise Exception("Diceengine exception: {}".format(message))

    @staticmethod
    def rollprop(dicenum, dicesides):
        """Generate probability distribution for the roll of dicenum dice with dicesides sides"""
        # TODO: do proper maths! This is easy stuff!
        results = Distrib({0: 1})
        # add dicenum dice
        for _ in range(dicenum):
            # Dictionary to store next probability distribution
            results_new = Distrib()
            # add every possible dice throw to every existing result
            for i in range(1, dicesides + 1):
                for value, prop in results.items():
                    results_new[value + i] += prop / dicesides
            results = deepcopy(results_new)
        return results

    @staticmethod
    def add(left, right):
        """Can add two diceprops or one diceprop and one integer or two integers"""
        # Note that adding is cumutative so it only has to be implemented one way

        if type(left) == int:
            if type(right) == int:
                # add int to int
                return left + right
            elif type(right) == list:
                # add int to list
                return [x + 2 for x in right]
            elif isinstance(right, Distrib):
                # add int to distrib
                new_distrib = Distrib()
                # add left to every key in Distrib
                for dice, prop in right.items():
                    new_distrib[dice + left] = prop
                return new_distrib
        elif type(left) == list:
            if type(right) == int:
                # has already been implemented
                return Diceengine.add(right, left)
        elif isinstance(left, Distrib):
            if type(right) == int:
                # has already been implemented
                return Diceengine.add(right, left)
            elif isinstance(right, Distrib):
                # add Distrib to Distrib
                new_distrib = Distrib()
                for d1, p1 in left.items():
                    for d2, p2 in right.items():
                        new_distrib[d1 + d2] += p1 * p2
                return new_distrib

        Diceengine.exception("Can't add {} to {}".format(type(left), type(right)))
      
    @staticmethod
    def greaterorequal(left, right):
        if type(left) == int and type(right) == int:
            return left >= right

        # for now the left must be a distribution:
        # TODO: call lessthen and switch sides if left side is an integer
        if not isinstance(left, Diceengine):
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
    d2 = Diceengine.rollprop(2, 2)
    print(d2)
