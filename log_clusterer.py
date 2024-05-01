import os
import re
import pandas
import numpy
import itertools
import dataclasses
import enum
import logging
logging.basicConfig(level=logging.INFO)

@dataclasses.dataclass
class Pattern:
    material: str
    substitution: str
    frequency: int

class Patterns(enum.Enum):
    '''Level 1'''
    character:   str = r'[\s\w]'

    # '''Level 2'''
    # blank:      str = r'\s'
    # word:   str = r'\w'

    # '''Level 3'''
    # alphabet:   str = r'[a-zA-Z_]'
    # digital:    str = r'[0-9]'
    # blank:      str = r'\s'

    # '''Level 4'''
    # _alphabet:   str = r'[_]'
    # alphabet:   str = r'[a-z]'
    # Alphabet:   str = r'[A-Z]'
    # digital:    str = r'[0-9]'
    # blank:      str = r'\s'
    
    symbol:  str = r'[^\s\w]'

class Processor:
    def __init__(self, patterns: Patterns):
        self.patterns = patterns

    @property
    def partition(self):
        patterns_members = Patterns.__members__ 
        parttion_pattern = '|'.join(
            '{pattern}+'.format(pattern=patterns_members.get(patterns_member).value)
            for patterns_member in patterns_members
        )
        parttion_pattern = f'({parttion_pattern})'
        return parttion_pattern

    def transform(self, material):
        logging.debug(material)

        for pattern in Patterns:

            if pattern != Patterns.symbol:
                logging.debug(pattern)

                if re.match(pattern.value, material):
                    return [
                        Pattern(
                            material=material,
                            substitution=next(iter(pattern.name)),
                            frequency=len(material)
                        )
                    ]
            else:
                logging.debug(pattern)

                return [
                    Pattern(
                        material=material,
                        substitution=next(group for group in sub.groups()),
                        frequency=len(sub.group())
                    )
                    for sub in re.finditer(
                        f'({pattern.value})\\1*',
                        material
                    )
                ]

if __name__ == '__main__':

    for root, directories, files in os.walk('logs'): 
        for file in files:

            file_log = os.path.join(root, file)
            file_cluster = os.path.join('clusters', f'{file}.md')

            processor = Processor(Patterns)

            with open(file_log) as file:
                transformations = (
                    (
                        line.rstrip('\n'),
                        tuple(
                            processor.transform(material)
                            for material in re.findall(
                                processor.partition,
                                line.rstrip('\n')
                            )
                        )
                    )
                    for line in file.readlines()
                )

            transformations = pandas.DataFrame(
                data=transformations,
                columns=['materials', 'transformations']
            )
            # Flatten collection of collection.
            transformations['transformations'] = transformations['transformations']\
                .apply(lambda transformation: tuple(itertools.chain.from_iterable(transformation)))
            # Generate representation.
            transformations['substitutions'] = transformations['transformations']\
                .apply(lambda instances: ''.join(instance.substitution for instance in instances))
            # Generate frequency of each sub-representation.
            transformations['frequencies'] = transformations['transformations']\
                .apply(lambda instances: ''.join(f'{instance.frequency}{instance.substitution}' if instance.frequency > 1 else instance.substitution for instance in instances))

            panel_data = pandas.DataFrame(
                [
                    {
                        'substitutions': substitution,
                        'materials': tuple(group['materials'].sort_values().unique()),
                        'frequencies': tuple(group['frequencies'].sort_values().unique()),
                        'occurences': len(group.index)
                    }
                    for substitution, group in transformations.groupby('substitutions')
                ]
            )

            panel_data = panel_data\
                .sort_values(['occurences'], ascending=False)\
                .reset_index(drop=True)


            with open(file_cluster, 'w') as file:
                for index, instance in panel_data.iterrows():
                    
                    file.write(f'# Section {index}' + '\n')

                    file.write('###### Substitution' + '\n')
                    file.write('\t' + instance.substitutions + '\n')

                    file.write('###### Frequency' + '\n')
                    for frequency in instance.frequencies:
                        file.write('\t' + frequency + '\n')

                    file.write('###### Material' + '\n')
                    for material in instance.materials:
                        file.write('\t' + material + '\n')
