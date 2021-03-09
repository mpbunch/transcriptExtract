"""
    HOW TO USE
    1. pip install any missing libraries
    2. google how to install ffmpgeg on my OS (maybe brew on osx?)
    3. audio files must be in .wav format
    4. find a sample wav file
    5. copy the wav file into the same directory as this script
    6. within terminal, use the following command
        python nameofscript.py -f the_name_of_wav_file.wav -c 50
"""
# Imports
# System, to gain access to command line arguments
import sys
# The main component of speech recognitionb
import speech_recognition as sr
# os and glob allow me to manipulate files on disk
import glob, os
# AudioSegment allows the developer to 'chunked' the audio sample
from pydub import AudioSegment
# after how many milliseconds of silence do we split, etc
from pydub.silence import split_on_silence
# Multiprocessing
#   Allows the software to use multiple processes
#   Using more than one cpu, you can parallelize your code
#   which of course reduces the computation time by
#   the number of processes.
import multiprocessing as mp
# Math is used to find the floor (round down) number
# of the audio records/processes to ensure there is
# no out of range error
# - there is probably a better way to do this
import math


def make_chunks(path):
    """
        Splitting the large audio file into chunks
    """
    # open the audio file using pydub
    sound = AudioSegment.from_wav(path)
    chunks = split_on_silence(sound,
                              # experiment with this
                              # value for your target audio file
                              min_silence_len=500,
                              # adjust this per requirement
                              silence_thresh=sound.dBFS-14,
                              # keep the silence for 1 second,
                              # adjustable as well
                              keep_silence=500,
                              )
    # currently the chunks are in memory
    return chunks


def make_transcript(chunks, process_id):
    """
        Making the actual transcript(s)
    """
    if not chunks[0]:
        # if there are no audio chunks return
        return

    # loop over chunks
    for i, audio_chunk in enumerate(chunks[0], start=1):
        # A slightly complex topic to cover in a comment
        # multiprocessing allows for parallel processing (good)
        # we can go fast (good)
        # but it also means that processes can happen in
        # any order (bad) for trying to create an ordered
        # transcript
        # So to get around the issue of order, I am relying
        # on file_name convention
        # {process_id} = [1, 2, 3, ...] global
        # {i} = chunk index [1, 2, 3] for each process
        # {input_name} = audiosample name (eg: class1audio)
        # what if you run two audio samples, you don't want them
        # overwritting each other
        # so you might end up with
        #   21_class1audio.wav
        #   01_class1audio.wav
        #   11_class1audio.wav
        #   02_class1audio.wav

        # At this point we don't care about the order of the audio files
        # but in the next step we will care about the transcript generation
        # so we do the work upfront to make the next step easy

        # sorry for the long winded note
        # #
        # create the chunk_filename
        chunk_filename = os.path.join(audio_folder_name,
                                      f"{process_id}{i}_{input_name}_chunk.wav")
        # check to see if the chunk_filename exists on disk
        # you may want to overwrite the file if it does exist
        # i chose to only write to disk if the file did not already exist
        # i thought it might speed it up slightly (it may not)
        if not os.path.isfile(chunk_filename):
            audio_chunk.export(chunk_filename, format="wav")

        # open each chunk_filename
        # you could probably do this with the audio bitestream
        # and do this fully in memory... maybe a future optimization
        with sr.AudioFile(chunk_filename) as source:
            # get the actual audio
            audio_listened = r.record(source)
            try:
                # because you are in a loop, you need to make sure
                # you reset the text value
                # for if the r.recognize_google function fails
                # you could get duplicate records in your transcript
                text = ''
                # try to get the text back
                # this does fail -- .. frequently-ish
                # i didn't look into it, as this is just for fun
                # but i would guess this code is too fast
                # and google doesn't like getting hammered by a single IP
                text = r.recognize_google(audio_listened)
            # if the r.recognize_google fails fail gracefully
            except sr.UnknownValueError as e:
                # print the error message to the terminal window
                print("Error:", str(e))
            else:
                # else SUCCESS!
                # we now have the text from the audio file!
                text = f"{text.capitalize()}."
                # output the text to the terminal window
                print(chunk_filename, ":", text)
        # if text is set, not null, not empty, not false
        if text:
            # open the tanscript_folder_destination/file.txt
            f = open(f'{trans_folder_name}/{process_id}{i}_{input_name}_log.txt', 'w+')
            # write the text to file
            f.write(text)
            # close the file
            f.close()
            # because we have extracted the text from the audio we no longer
            # need the audio file we clean up after ourselves,
            # and remove the audio_chunk file
            os.remove(f'{audio_folder_name}/{chunk_filename}')


def merge_transcripts():
    """
        We currently have many many individual transcript files
        and we need to combine them all into a single organized
        file so it makes human readable sense.
    """
    # change directory into the transcript_folder
    os.chdir(trans_folder_name)
    # get all transcript_files that match our current filename
    # schema (we could be running more than one of these at a time)
    # magic happens here
    # sorted() is the crux of this entire operation
    # files may not be/ are not pulled in order
    # so we need to sort them in logical order
    # I mention this in detail within the make transcript function
    files_to_merge = sorted(glob.glob(f"*_{input_name}_log.txt"))
    # make a **_complete.txt file within the transcript directory
    f = open(f'{input_name}_log_complete.txt', 'w+')
    # loop over each individual transcript file
    for fname in files_to_merge:
        with open(fname) as infile:
            # loop over each line within each transcript file
            # our usecase only ever has 1 line
            # but this is a bit future proof as i figured
            # i may add more logic later and forget this step
            for line in infile:
                # wirte each line to the complete transcript file
                f.write(line)
                # add a new line character so each line is on a new line
                f.write('\n')
        # remvoe the individual transcript file after the text
        # has been added to the complete transcript file
        os.remove(fname)
    # close the complete transcript file
    f.close()


if __name__ == "__main__":
    """
        Variables are all set here
            path is required
    """
    # These are ternary operators
    # they read as follows
    # (condition true stuff) if (condidtion) else (condition false stuff)
    # path is the source audio path (what we want to convert to a transcript)
    path = sys.argv[sys.argv.index('-f')+1] if '-f' in sys.argv else None
    # how many threads do we want working on this task
    # i used 100, but i have a fairly beefy machine
    # start with 25-50 and see if you machine slows to a halt or powers through
    threads = int(sys.argv[sys.argv.index('-c')+1]) if '-c' in sys.argv else mp.cpu_count()
    # audio folder path, you can change this
    audio_folder_name = "audio-chunks"
    # transcript folder path, you can change this
    trans_folder_name = "transcripts"

    # path is required
    # if there is no source path.. what are we doing..
    if path:
        # these variable act as 'global' variables from other languages
        # im honestly not 100% sure what they are called in python
        # create the input_name
        input_name = path[:-4]
        # init Recognizer
        r = sr.Recognizer()
        # create the audio_chunk_folder, so we can write to it later
        # if it doesn't already exist
        if not os.path.isdir(audio_folder_name):
            # actually make the directory
            os.mkdir(audio_folder_name)
        # make the transcript folder, so we can write to it later
        # if it doesn't already exist
        if not os.path.isdir(trans_folder_name):
            # actually make the directory
            os.mkdir(trans_folder_name)

        # get all of the chunks from the source audio file
        chunks = make_chunks(path)
        # how many chunked audio files are there
        # so we can split them evenly across all of the processes
        len_chunks = len(chunks)
        # if the audio sample has no chunks ... what are we doing ...
        if chunks:
            # variable abuse is not best practice, don't do as i do
            # set the number of threads to whatever is lower
            # either the threads desired, or the len_chunks
            # that way the minimum number of chunks per thread is 1
            threads = threads if threads <= len_chunks else len_chunks
            # get the math.floor of len_chunks/threads
            # because you don't want an offset issue
            # or a division issue when trying to evenly
            # dole out the chunks
            # records = records per thread
            records = math.floor(len_chunks/threads)

            # main magic starts here
            # the target is the main make_transcript function
            # args is hard to read, i will try to break it down
            # first, if you don't use list comprehension, google that first
            # welcome back
            # for x in range(threads), a generic for loop
            #   x = 0 to number of threads specified
            # chunks[x*records:(x+1)*records]
            #   x = 0
            #   chunks[0:1*records]
            #       if records = 50
            #           chunks[0:50] this gets the first 50 chunks from chunks
            #   x=1
            #   chunks[50:100]
            #   ... repeat
            # you are thinking, you IDIOT, you are calculating a record twice
            # ah ah ah (think jurassic park)
            # the first value [50:100] does not include 50 itself
            processes = [mp.Process(target=make_transcript,
                                    args=([chunks[x*records:(x+1)*records]], x)) for x in range(threads)]
            # loop over and start each process
            for p in processes:
                p.start()
            # you can read the docs for this one
            # but basically wait until all similar process
            # are done running
            for p in processes:
                p.join()

            # merge all of the individual transcripts into a single
            # transcript doc
            merge_transcripts()
            # HUZZAH we are done!
            print(f' -- !! DONE !! --')
            # Your transcript file can be found here
            print(f'Transcript found at: {trans_folder_name}/{input_name}_log_complete.txt')
        else:
            # if no chunks are found, raise an exception
            raise Exception(f'There was an issue chunking the audio sample.')

    else:
        # if no f (audio file) is provided, raise an exception
        raise Exception(f'-f file path is required, /path/to/file.wav')
