#!/usr/bin/env python3

#    Copyright 2017 Vidas Simkus
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#

import os.path
import sys
import subprocess
import io
import importlib
import datetime
import json

class SourceFile(object):
	"""
	Class representing a single to be compiled source file
	"""

	def __init__(self,_file_name):
		"""
		Constructor
		"""
		self.full_file_name = _file_name
		self.directory = os.path.dirname(self.full_file_name)
		self.base_name = os.path.basename(self.full_file_name)
		self.file_name,self.file_extension = os.path.splitext(self.base_name)

		return

	def does_exist(self,_dir):
		"""
		Returns True if the file exists, False otherwise
		"""

		fn = None
		if _dir is not None:
			fn = os.path.join(_dir,self.full_file_name)
		else:
			fn = self.full_file_name

		return os.access(fn,os.R_OK)

	def change_extension(self,_ext,_with_dir = True):
		"""
		Returns the string file name with the specified extension.  Instance is not modified.
		"""

		fn = None

		if _with_dir is False:
			fn = self.file_name
		else:
			fn = os.path.join(self.directory,self.file_name)

		if _ext.startswith("."):
			return fn + _ext
		else:
			return fn + "." + _ext

class Context(object):

	#
	#
	#
	LIB_TARGET = None

	#
	#
	#
	EXE_TARGET = None

	#
	# Include directories to add to the tool chain parameters
	#
	INCLUDE_DIRS = []

	#
	# Library directories to add to the tool chain parameters
	#
	LIB_DIRS = []

	#
	# List of source files.  Each source file must be instance of SourceFile
	#
	SOURCE_FILES = []

	#
	# List of libraries to add during linking stage
	#
	LIBRARIES = []

	#
	# Target name prefix.  Automatically handled.  Don't set this to None.
	#
	TARGET_PREFIX = ""

	#
	# Directory containing all of the source files.  Will be automatically prepended to the SourceFile path.
	#
	SOURCE_DIR="src"

	#
	# Output makefile name
	#
	MAKEFILE="Makefile"

	#
	# Binary output directory.  Will be automatically prepended to the object file and final output binary paths and so forth
	#
	OUTPUT_DIR="bin"

	#
	# CXX compilation flags
	#
	CXX_FLAGS=["-g","-g3","-pedantic","-pedantic-errors","-Wall","-Wextra","-Werror","-Wconversion","-Wunused-parameter","-Wsign-compare","-std=c++17","-fPIC","-fexceptions"]
	#LINK_FLAGS = ["-fexceptions"]

	LINK_FLAGS = []
	LINK_SYS_LIBS = []

	#
	# List of related projects that a project needs to compile.  An entry is a string instance to the projects base directory
	#
	RELATED_PROJECTS = None

	#
	# Projects tag.  Should be ASCII alphabet characters only with no spaces, numbers, or punctuation, or anything else weird.
	#
	TAG = None

	#
	# Preprocessor dependency generation flags
	#
	CXX_DEPEND_FLAGS=["-MM"]

	#
	# Tool chain flag for generating a shared library
	#
	CXX_LIB_FLAGS=["-shared"]

	#
	# Tool chain flag for generating an executable
	#
	CXX_EXE_FLAGS = []

	TOP_LEVEL = True

	THREADS = True

	#
	# C++ compiler
	#
	CXX=""

	LD=""


	def get_include_dirs(self):
		return list(self.INCLUDE_DIRS)

	def __init__(self):
		self.makefile_fd = None
		self.json_fd = None
		self.working_dir = os.getcwd()

		# JSON object for compile_commands.json for clangd integration

		self.compile_commands = []


	def make_dep_file_name(self,_file):
		"""
		Returns a dependency output file name based on the supplied SourceFile instance.
		Method combines OUTPUT_DIR and file name and changes the file extension to '.d'.
		@param _file SourceFile instance
		"""

		return os.path.join(self.OUTPUT_DIR,_file.change_extension(".d"))

	def make_source_file_name(self,_file):
		"""
		Returns a source file name based on the supplied SourceFile instance.
		Method combines SOURCE_DIR and file name in the SourceFile instance.
		@param _file SourceFile instance
		"""

		return os.path.join(self.SOURCE_DIR,_file.full_file_name)

	def make_object_file_name(self,_file):
		"""
		Returns an object file name based on the supplied SourceFile instance.
		Method combines OUTPUT_DIR and file name and changes the file extension to '.o'
		@param _file SourceFile instance
		"""

		return os.path.join(self.OUTPUT_DIR,_file.change_extension(".o"))

	def make_include_parms(self):
		"""
		Returns an array of include dirs and -I paramters.
		"""

		ret = []

		for f in self.INCLUDE_DIRS:
			if f is not None:
				ret.append("-I" + f)

		return ret

	def make_cxx_flags(self):
		"""
		Returns a string representation of all of the CXX_FLAGS
		"""

		parms = list(self.CXX_FLAGS)

		if self.THREADS is True:
			parms += ["-pthread",]

		return parms


	def make_cxx_lib_flags(self):
		"""
		Returns a string representation of all of the CXX_LIB_FLAGS.  This is used during the linking phase of a library creation.
		"""

		parms = list(self.CXX_LIB_FLAGS)

		if self.THREADS is True:
			parms += ["-lpthread",]



		return " " + " ".join(parms) + " "

	def make_cxx_exe_flags(self):
		"""
		Returns a string representation of all of the CXX_EXE_FLAGS.  This is used during t he linking phase of an executable.
		"""

		parms = list(self.CXX_EXE_FLAGS)

		if self.THREADS is True:
			parms += ["-lpthread",]


		return " "+ " ".join(parms) + " "

	def make_cxx_lib_dir_flags(self):
		ret = []

		for f in self.LIB_DIRS:
			ret.append("-L" + f)

		return " " + " ".join(ret) + " "

	def make_cxx_link_lib_flags(self):
		ret = []

		for f in self.LIBRARIES:
			ret.append("-l" + f)

		return " " + " ".join(ret) + " "

	def make_cxx_link_flags(self):
		return " " + " ".join(self.LINK_FLAGS) + " "


	def write_makefile(self):
		"""
		Writes out the "middle" portion of the makefile
		"""

		#
		# If this is the main Makefile, we specify the all: target
		#
		if self.TOP_LEVEL:
			self.makefile_fd.write("#\n# Top-level project targets\n#\n\n")

			if self.TAG is not None and len(self.TAG) > 0:
				self.makefile_fd.write("all: " + self.TARGET_PREFIX + "all\n\n");
				self.makefile_fd.write("clean: " + self.TARGET_PREFIX + "clean\n\n");

		#
		# Generate all object recipes
		#

		# Main target i.e. THING_all
		# The all: target in the Makefile references this target.
		# This is where we link all the disparate object files together.
		self.makefile_fd.write(self.TARGET_PREFIX + "all: " + self.TARGET_PREFIX +  "all_o\n")

		if self.LIB_TARGET is not None:
			lt = self.LIB_TARGET
			if not lt.startswith("lib"):
				lt = "lib" + lt

			if not lt.endswith(".so"):
				lt += ".so"

			lt = os.path.join(self.OUTPUT_DIR,lt)

			self.makefile_fd.write("\t" + self.CXX + " " + " ".join(self.make_cxx_flags())
			 + self.make_cxx_lib_flags() + " -o " + lt + " ")

			for f in self.SOURCE_FILES:
				self.makefile_fd.write(" " + self.make_object_file_name(f))

		elif self.EXE_TARGET is not None:
			self.makefile_fd.write("\t" + self.LD + self.make_cxx_link_flags() + " -o " + self.EXE_TARGET + " " )

			for f in self.SOURCE_FILES:
				self.makefile_fd.write(" " + self.make_object_file_name(f))

			self.makefile_fd.write(self.make_cxx_lib_dir_flags() + self.make_cxx_link_lib_flags() + self.make_cxx_exe_flags() );
			self.makefile_fd.write(" " + " ".join(self.LINK_SYS_LIBS));
		else:
			raise RuntimeError("Either LIB_TARGET or EXE_TARGET needs to be specified.  Please fix.")

		self.makefile_fd.write("\n")
		self.makefile_fd.write("\n")

		self.makefile_fd.write(self.TARGET_PREFIX + "all_o: ")
		self.makefile_fd.write(self.TARGET_PREFIX + "make_dirs ")

		for f in self.SOURCE_FILES:
			self.makefile_fd.write(self.make_object_file_name(f) + " ")
			self.makefile_fd.write(" ")

		self.makefile_fd.write("\n\n");

		#
		# Generate 'clean' recipe
		#

		self.makefile_fd.write(self.TARGET_PREFIX + "clean: \n")
		self.makefile_fd.write("\t@echo Cleaning stuff.\n")
		for f in self.SOURCE_FILES:
			self.makefile_fd.write("\t- @rm " + self.make_object_file_name(f) + " 2> /dev/null || true\n")

		if self.LIB_TARGET is not None:
			self.makefile_fd.write("\t- @rm " + self.LIB_TARGET + " 2> /dev/null || true\n")
		elif self.EXE_TARGET is not None:
			self.makefile_fd.write("\t- @rm " + self.EXE_TARGET + " 2> /dev/null || true\n")

		self.makefile_fd.write("\n");

		#
		# Generate 'make dirs' recipe
		#

		made_dirs = []

		self.makefile_fd.write(self.TARGET_PREFIX + "make_dirs: \n" )

		for f in self.SOURCE_FILES:
			d = os.path.join(self.OUTPUT_DIR,f.directory)
			if d not in made_dirs:
				self.makefile_fd.write("\t- @mkdir -p " + d + "\n")
				made_dirs.append(d)

	def write_makefile_header(self):
		"""
		Writes out the header portion of the makefile
		"""

		print ("""
#
# This file is mechanically generated.  Any changes will most likely be lost.
#""",file=self.makefile_fd)

		print ("# File generated on: " + datetime.datetime.now().isoformat(),file=self.makefile_fd)
		print ("#\n",file=self.makefile_fd)


	def write_makefile_footer(self):
		"""
		Writes out the footer portion of the makefile
		"""

		print ("""
#
# EOF
#
		""", file=self.makefile_fd)

	def init(self):
		"""
		Initializes the context instance
		"""

		if self.TAG is not None and len(self.TAG) > 0:
			self.TARGET_PREFIX = self.TAG + "_"

		if isinstance(self.INCLUDE_DIRS,tuple):
			self.INCLUDE_DIRS = list(self.INCLUDE_DIRS)

		self.makefile_fd = io.StringIO()
		self.json_fd = io.StringIO();

		self.write_makefile_header()

		if self.RELATED_PROJECTS is not None:
			for p in self.RELATED_PROJECTS:
				ctx = import_project(p)

				if ctx is None:
					return False

				ctx.TOP_LEVEL = False

				print ("Processing related project in: " + ctx.working_dir)
				rpath = os.path.join(ctx.working_dir,ctx.OUTPUT_DIR)

				for d in ctx.INCLUDE_DIRS:
					id = os.path.join(p,d)
					self.INCLUDE_DIRS += [id,]

				if ctx.LIB_TARGET is not None and len(ctx.LIB_TARGET) > 0:
					lib_file = SourceFile(ctx.LIB_TARGET)

					self.LIBRARIES.append(lib_file.base_name)
					self.LIB_DIRS.append(os.path.join(p,ctx.OUTPUT_DIR))
					self.LINK_FLAGS += ["-rpath",rpath]


	def finalize(self):
		"""
		Finalizes the context instance
		"""

		self.makefile_fd.close()

	def __str__(self):
		return str(self.TAG) + ":"

class GCCContext(Context):
	#
	# C++ compiler
	#
	CXX="g++"

	LD="g++"

	def __init__(self):
		super(GCCContext,self).__init__()

class CLANGContext(Context):
	#
	# C++ compiler
	#
    CXX="clang"

    LD="clang"

    LINK_SYS_LIBS = ["-lstdc++"]

    def __init__(self):
        super(CLANGContext,self).__init__()

        if sys.platform == "freebsd11" or sys.platform == "freebsd12":
            CLANGContext.CXX = "clang"
            CLANGContext.LD = "clang"
        else:
            # Some versions of Linux do not have a newline character in the version string...            

            vs = sys.version.split('\n');

            if len(vs) < 2:
                vs = vs[0]
            else:
                vs = vs[1]

            if vs.startswith("[GCC 6.3"):
                # Ugly hack to see if we're on beaglebone
                CLANGContext.CXX = "clang-7"
                CLANGContext.LD = "clang-7"

########################################################

def import_project(_dir):
	"""
	Imports a VC.py project file from the specified directory
	@return An instance of the context
	"""

	# Check for existence of the module
	f = os.path.join(_dir,"VC.py")
	if not os.access(f,os.R_OK):
		print  ("VC.py does not exist.  Please fix",file = sys.stderr)
		return None

	# Save a copy of the system path
	old_path = list(sys.path)

	# Add the path of the module as the first element
	sys.path.insert(0,_dir)

	m = None

	try:
		m = importlib.import_module("VC")
	except Exception as e:
		print ( "Failed to load configuration file VC.py: " + str(e),file = sys.stderr)
		return None

	# Restore system path
	sys.path = list(old_path)
	ctx = m.vc_init()

	# Cleanup after ourselves because we may need to load VC.py for other projects.
	del m
	del sys.modules["VC"]

	ctx.working_dir = os.path.abspath(_dir)

	return ctx

def verify_output_paths(_ctx):
	if not os.path.exists(_ctx.OUTPUT_DIR):
		os.makedirs(_ctx.OUTPUT_DIR)

	for f in _ctx.SOURCE_FILES:
		d = os.path.join(_ctx.OUTPUT_DIR,f.directory)

		if not os.path.exists(d):
			os.makedirs(d)

	return

def check_source_files(_ctx):
	rc = True
	for f in _ctx.SOURCE_FILES:
		if not f.does_exist(_ctx.SOURCE_DIR):
			print ("File not readable: " + str(f.full_file_name),file=sys.stderr)
			rc = False

	return rc

def generate_dependencies(_ctx):
	"""
	Generates the individual .o targets in the make file
	"""
	cmd = []

	if(len(_ctx.CXX) < 1):
		raise Exception("CXX is not specified")

	cmd += [_ctx.CXX] +  _ctx.make_include_parms()

	cmd += _ctx.CXX_DEPEND_FLAGS + _ctx.CXX_FLAGS

	json_object = {}
	json_object["directory"] = _ctx.working_dir

	for f in _ctx.SOURCE_FILES:
		#
		# Loop through each individual source file
		#

		json_object["file"] = _ctx.make_source_file_name(f)

		b = ""
		wcmd = cmd + ["-MT",_ctx.make_object_file_name(f),_ctx.make_source_file_name(f)]
		print ("\nGenerating dependency using: \n" + repr(wcmd))

		p = subprocess.Popen(wcmd,stdin=None,stderr=subprocess.PIPE,stdout=subprocess.PIPE)
		p.wait()

		if p.returncode != 0:
			for l in p.stderr:
				b += l.decode("utf-8")

			print ("Failed to process dependencies, code: " + str(p.returncode),file=sys.stderr)
			print ("cmd: " + " ".join(wcmd),file=sys.stderr)
			print (b,file=sys.stderr)


			return False
		else:
			_ctx.makefile_fd.write("\n")

			#
			# Loop through each individual dependency line generated by wcmd above and put it into the Makefile
			#
			for l in p.stdout:
				_ctx.makefile_fd.write(l.decode("utf-8"))

			jo = {}

			#
			# Put out the actual compilation line for the object
			#

			args =[]
			args.append(_ctx.CXX)
			args += _ctx.make_include_parms()
			args += _ctx.make_cxx_flags()
			args += ["-c",]
			args.append(_ctx.make_source_file_name(f))
			args += ["-o",]
			args.append(_ctx.make_object_file_name(f))

			json_object["arguments"] = args

			_ctx.makefile_fd.write("\t" + " ".join(args) + "\n")


			#print("Compile line:\n" + repr(args))

			_ctx.compile_commands.append(json_object)


	j = json.JSONEncoder(indent=2)
	_ctx.json_fd.write(j.encode(_ctx.compile_commands))

	return True

def process(_ctx):
	_ctx.init()

	if not check_source_files(_ctx):
		print ("Failed file check", file=sys.stderr)
		sys.exit(-1)

	verify_output_paths(_ctx)

	_ctx.write_makefile()

	generate_dependencies(_ctx)

	_ctx.write_makefile_footer()

	make_str =  _ctx.makefile_fd.getvalue()
	json_str = _ctx.json_fd.getvalue()

	_ctx.finalize()

	return make_str,json_str

sys.dont_write_bytecode = True


if __name__ == "__main__":

    print ("Currently in: " + os.getcwd())
    ctx = import_project(os.getcwd())

    if ctx is None:
        # We failed 
        exit(-1)

    mstr,jstr = process(ctx)
    mfd = open("Makefile","wt")
    jfd = open("compile_commands.json","wt")

    mfd.write(mstr)
    jfd.write(jstr)

    mfd.close()
    jfd.close()
