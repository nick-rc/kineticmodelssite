"""
Run this like so:
 $  python import_prime.py /path/to/local/mirror/warehouse.primekinetics.org/
 
It should dig through all the prime XML files and import them into
the Django database.
"""

import os
from xml.etree import ElementTree  # cElementTree is C implementation of xml.etree.ElementTree, but works differently!
from xml.parsers.expat import ExpatError  # XML formatting errors

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "kineticssite.settings")
import django
django.setup()

from kineticmodels.models import Kinetics, Reaction, Stoichiometry, \
                                 Species, KinModel, Comment, \
                                 Source, Author, Authorship


def main(top_root):
    """
    The main function. Give it the path to the top of the database mirror
    """
    print "Starting at", top_root
    for root, dirs, files in os.walk(top_root):
        if '.git' in dirs:
            dirs.remove('.git')
        if root.endswith('depository/bibliography/catalog'):
            print "We have found the depository/bibliography/catalog which we can import!"
            import_bibliography(root, files)
        else:
            # so far nothing else is implemented
            print "Skipping {}".format(root)

def import_bibliography(root, files):
    "Import the list of bibliography files 'files' in the folder 'root'."
    for file in files:
        filepath = os.path.join(root, file)
        import_bibliography_file(filepath)

def import_bibliography_file(filepath):
    """
    Import the bibliography file from the given filepath, into Django database
    
    Parsing the XML file, using Element Tree method
    see https://docs.python.org/2/library/xml.etree.elementtree.html for details
    """
    print "Parsing file {}".format(filepath)

    try:
        tree = ElementTree.parse(filepath)
    except ExpatError as e:
        print "[XML] Error (line %d): %d" % (e.lineno, e.code)
        print "[XML] Offset: %d" % (e.offset)
        raise
    except IOError as e:
        print "[XML] I/O Error %d: %s" % (e.errno, e.strerror)
        raise

    ns = {'prime': 'http://purl.org/NET/prime/'}  # namespace
    bibitem = tree.getroot()
    primeID = bibitem.attrib.get("primeID")
    dj_item, created = Source.objects.get_or_create(bPrimeID=primeID)  # dj_ stands for Django

    # Every source should have a title:
    dj_item.source_title = bibitem.findtext('prime:title', namespaces=ns, default='')

    # There may or may not be a journal, so have to cope with it being None
    dj_item.journal_name = bibitem.findtext('prime:journal', namespaces=ns, default='')

    # There seems to always be a year in every prime record, so assume it exists:
    dj_item.pub_year = bibitem.findtext('prime:year', namespaces=ns, default='')
    
    # Some might give a volume number:
    dj_item.jour_vol_num = bibitem.findtext('prime:volume', namespaces=ns, default='')
    
    # Some might give page numbers:
    dj_item.page_numbers = bibitem.findtext('prime:pages', namespaces=ns, default='')
    
    # No sources in PrIMe will come with Digital Object Identifiers, but we should include this for future importing:
    dj_item.doi = bibitem.findtext('prime:', namespaces=ns, default='')

    "ToDo: should now extract the other data from the bibitem tree, and add to the dj_item, like examples above"
    dj_item.save()

    for index, author in enumerate(bibitem.findall('prime:author', namespaces=ns)):
        number = index + 1
        print "author {} is {}".format(number, author.text)
        dj_author, created = Author.objects.get_or_create(name=author.text)
        authorship, created = Authorship.objects.get_or_create(source=dj_item, order=number)
        authorship.author = dj_author
        authorship.save()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Import PRIME database mirror into Django.')
    parser.add_argument('root', metavar='root', nargs=1,
                       help='location of the mirror on the local filesystem')
    args = parser.parse_args()
    top_root = os.path.normpath(os.path.abspath(args.root[0]))  # strip eg. a trailing '/'
    main(top_root)