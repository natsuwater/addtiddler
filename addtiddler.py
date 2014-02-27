"""
This script adds a new tiddler with an optional embedded image either to
an existing TiddlyWiki or to a new TiddlyWiki.

From the command line
---------------------
Example usage from the commandline (should all be on one line):

python addtiddler.py -i test.html --description "Test image.  Code to 
generate image was: {{{plot(x,y)}}}" --image figures/plot1.png --tags 
"images timeseries depth temperature"

Or:

python addtiddler.py -i test.html -o new.html --description "Test 
image" --image figures/plot1.png --tags "images 
timeseries depth temperature" --resize

Use:
 
    python addtiddler.py -h

to view additional help.

From another script
-------------------
>>> from addtiddler import addtiddler
>>> addtiddler('mywiki.html', image='figures/plot1.png', 
                tags='images timeseries depth temperature',
                resize=True)


from addtiddler import addtiddler
addtiddler('ImageCatalogue.htm', image="noise04_ex.png", tags='coil snr',
	   title='Test', author='NatsuMizu', description="Mytest for logging")


COPYRIGHT INFORMATION

Copyright (c) 2008 Ryan Dale

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.



"""
import datetime
import sys
import os
import re
import shutil
import types ## NM
from optparse import OptionParser

try:
    from PIL import Image
    PIL_imported = True
except ImportError:
    print "Can't find installed Python Imaging Library (http://www.pythonware.com/products/pil/index.htm).  Auto-resizing is now disabled."
    PIL_imported = False

class TiddlyWikiChunk(object):
    """
    A simple class that knows how to pull the title and tags out of a
    block of code, and knows whether or not it's a 
    tiddler or just plain source code (check to see if the isTiddler 
    attribute is True).
    
    The itertiddler function creates an iterator of these objects.
    """
    
    title_regexp = re.compile('title="(.*?)"')
    tags_regexp = re.compile('tags="(.*?)"')
    
    def __init__(self, sourceCode):
        """Initialization for TiddlyWikiChunk"""
        self.sourceCode = sourceCode
        self.contents = None
        self.tags = None
        title_match = TiddlyWikiChunk.title_regexp.search(self.sourceCode)
        if title_match:
            self.title = title_match.group(1)
        else:    
            self.title = None

        tags_match = TiddlyWikiChunk.tags_regexp.search(self.sourceCode)
        if tags_match:
            self.tags = tags_match.group(1)
        else:
            self.tags = None

        if self.title is not None:
            self.isTiddler = True
        else:
            self.isTiddler = False
    def __repr__(self):
        "String representation of TiddlyWikiChunk."
        if self.title is not None:
            return 'TWChunk object: "%s"' % self.title
        else:
            return 'TWChunk object: Source = "%s..."' % self.sourceCode[:6]

def itertiddler(s):
    """
    Given an open file, this function returns a generator of
    TiddlyWikiChunk objects. 
    Thanks to Andrew Dalke, 
    http://www.dalkescientific.com/writings/NBN/iterators.html
    for iterator ideas.
    """

    saved = None
    while 1:
        
        # Enter this loop the first time, but not again until 
        # the inner loop sees another '<div title'.

        if saved is not None:
            line = saved
            saved = None
        else:
            line = s.readline()  # read a line only if "saved" has something, which will 
                                 # only be the case when a new tiddler is started.
            if not line:
                return  # EOF reached.

        #if not line.startswith('<div title'):
            #break
            #yield TiddlyWikiChunk(line)
            #raise TypeError('Gotta start a title with <div title')

        divs = []
        
        divs.append(line)  # make sure the first line is the div definition . . .
        
        while 1:
            line = s.readline()
            if not line:
                break # EOF reached.
            if line.startswith('<div title'):
                # Break out of this loop because you found the start of a tiddler.
                saved = line
                break 

            # Otherwise, keep writing the line.
            divs.append(line)

            if '</div>' in line:
                saved = None
                break

        t = TiddlyWikiChunk(''.join(divs))

        yield t 

def addtiddler(infile, outfile=None, image=None, description='', tags='', author='author', title=None, resize=False, replace=False, UTC_offset=0):
    """
    Function to add a new tiddler to an existing TiddlyWiki file.

    :Parameters:
        infile
            Input file.
        outfile
            Output file. If unspecified, the input file will be overwritten.
        image : string
            The path name of the image file to embed.  This path should be
            relative to the output file (or to the input file, if no
            output was specified).
        description : string
            The text that will be added to the tiddler
        tags : string
            Space-delimited string of tags
        author : string
            Author's name.  Default is 'author'.
        title : string
            The title for the tiddler
        resize : boolean
            Resize the image to a max of 500px
        replace : boolean
            Automatically replace a tiddler of the same name with this tiddler.
        UTC_offset : integer
            Number of hours offset from UTC time, e.g., -5 for EST
    """
    if outfile is None:
        outfile = infile+'.tmp'
        tempfile = True
    
    if title is None:
        if image is not None:
            title = image
        elif image is None:
            title = 'New Tiddler'
    
    
    # Change to output file dir so that image path will be relative to output file.
    outfilepath = os.path.realpath(outfile)
    outfiledir, outfilename = os.path.split(outfilepath)
    original_cwd = os.getcwd() # save current working directory in order to get back here when done.
    os.chdir(outfiledir) # change to the output file's directory so that the image path will be relative to the output.

    # Now that we're here, strip the directory info off of outfile.
    infile = os.path.basename(infile)
    outfile = os.path.basename(outfile)


    # Resize image if requested.
    if resize and PIL_imported and image is not None:
        filename, ext = os.path.splitext(image)
        new_filename = filename + '.thumb.png'
        im = Image.open(image)
        sz = (500, 500)
        im.thumbnail(sz, Image.ANTIALIAS)
        im.save(new_filename, "PNG")
        image = new_filename
        

    # Create a new tiddler . . . 
    d = {}  # d is a dictionary that will be used to fill in the tiddler content.
    d['tags'] = tags
    modification_time = datetime.datetime.now() + datetime.timedelta(0,UTC_offset) 
    d['modified'] = modification_time.strftime('%Y%m%d%H%M')
    d['created'] = d['modified']
    d['title'] = title
    d['author'] = author
    d['changecount'] = 1

    if image is not None:
        htmlth = "&lt;html&gt;"
        imgth = "&lt;img src=&quot;"
        imgtt = "&quot; style=&quot;width: 640px; &quot;/&gt;"
        htmltt = "&lt;/html&gt; \n"
        ## d['text'] = "[img[%s]]\n%s" % (image, description)
        ## Modification by N. Mizutani on 08 Oct. 2008
        if type(image) == types.ListType:
            d['text'] = htmlth + "\n".join(
                [imgth + i + imgtt for i in image]
                ) + htmltt + description
        else:
            d['text'] = (htmlth + imgth + image + imgtt + htmltt + description)
    else:
        d['text'] = description

    # Tiddler creation:
    # Create the text string for the complete tiddler (HTML tags and everything) by filling in dictionary d.
    tiddler_source = """<div title="%(title)s" modifier="%(author)s" modified="%(modified)s" created="%(created)s" tags="%(tags)s" changecount="%(changecount)s">
    <pre>%(text)s</pre></div>
    """ % d
    
    # Read everything in from infile as a list of TiddlyWikiChunks.
    fin = open(infile)
    twchunks = itertiddler(fin)

    # Open output file for writing (if no output file was specified, this is the same as the input 
    # file that was just read in)
    fout = open(outfile, 'w')

    # As long as the current chunk does not represent a tiddler, write the contents of it to fout.
    # When you reach one that IS a tiddler, then pause . . . 
    for chunk in twchunks:
        if chunk.title == title:
            if replace:
                continue
            elif not replace:
                answer = raw_input('Another tiddler with the name "%s" was found.  Delete it? (y/n) ' % chunk.title)
                if answer == 'y':
                    continue
        fout.write(chunk.sourceCode)
        if '<div id="storeArea">' in chunk.sourceCode:
            break  # note that break is after it's already been written.
             
    
    fout.write(tiddler_source)  # . . . write the new tiddler to fout . . .
    

    # . . . then continue copying the remaining chunks to the output file.  
    # Since twchunks is an iterator, it picks up where it left off last. 

    for chunk in twchunks:
        # If the title of the tiddler just added is the same as an existing one,
        # prompt the user for deletion.
        if chunk.title == title:
            if replace:
                continue
            elif not replace:
                answer = raw_input('Another tiddler with the name "%s" was found.  Delete it? (y/n) ' % chunk.title)
                if answer == 'y':
                    continue

        # Otherwise, write it out to file.
        fout.write(chunk.sourceCode)

    # Done.
    fout.close()
    fin.close()
    
    # Overwrite input file with output file, if no output was specified. (tempfile was
    # set at the beginning of this function)
    if tempfile:
       shutil.move(outfile, infile) 
        
    # Return from whence you came
    os.chdir(original_cwd)

if __name__ == "__main__":

    # Parse commandline arguments if this module is run as a script.
    parser = OptionParser()
    parser.add_option('-i', 
                        action='store', 
                        dest='infile', 
                        help='Relative path to input TiddlyWiki file.')
    parser.add_option('-o', 
                        action='store', 
                        dest='outfile', 
                        help='Relative path to output TiddlyWiki file.  If not specified, tiddler will be added to INPUT.')
    parser.add_option('--title', 
                        action='store',
                        dest='title',
                        help='Optional title for the new Tiddler.  Default is image path (if provided), otherwise "New Tiddler".')
    parser.add_option ('--description', 
                        action='store', 
                        default='', 
                        dest='description', 
                        help='Text to be added below the image in the tiddler. Can be any valid TiddlyWiki syntax.')
    parser.add_option('--image', 
                        action='store', 
                        dest='image', 
                        help='Path to image, relative to OUTPUT.')
    parser.add_option('--tags', 
                        action='store', 
                        dest='tags', 
                        default='', 
                        help='Quoted space-delimited tags for this tiddler.  Ex: --tags "images temperature depth"')
    parser.add_option('--resize', 
                        action='store_true', 
                        dest='resize', 
                        default=False, 
                        help='Option to auto-resize the image to 400px. By default this is disabled. Will create a new image in the folder with "thumb" appended to filename, and will use that thumbnail as the image for the tiddler.')
    (options, args) = parser.parse_args()

    addtiddler(infile=options.infile, 
                outfile=options.outfile, 
                image=options.image, 
                description=options.description, 
                tags=options.tags, 
                title=options.title,
                resize=options.resize)
