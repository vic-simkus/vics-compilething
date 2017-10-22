#!/usr/bin/env python

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
import StringIO
import importlib
import datetime

class SourceFile:
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

class Context:

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
	CXX_FLAGS=["-g","-g3","-pedantic","-pedantic-errors","-Wall","-Wextra","-Werror","-Wconversion","-Wunused-parameter","-Wsign-compare","-std=c++11","-fPIC","-fexceptions"]
	LINK_FLAGS = ["-fexceptions"]

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

	#
	# C++ compiler
	#
	CXX="g++"

	LD="g++"

	def get_include_dirs(self):
		return list(self.INCLUDE_DIRS)

	def __init__(self):
		self.makefile_fd = None

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
		return " " + " ".join(self.CXX_FLAGS) + " "

	def make_cxx_lib_flags(self):
		"""
		Returns a string representation of all of the CXX_LIB_FLAGS
		"""
		return " " + " ".join(self.CXX_LIB_FLAGS) + " "

	def make_cxx_exe_flags(self):
		"""
		Returns a string representation of all of the CXX_EXE_FLAGS
		"""
		return " "+ " ".join(self.CXX_EXE_FLAGS) + " "

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

		if self.TOP_LEVEL:
			self.makefile_fd.write("#\n# Top-level project targets\n#\n\n")

			if self.TAG is not None and len(self.TAG) > 0:
				self.makefile_fd.write("all: " + self.TARGET_PREFIX + "all\n\n");
				self.makefile_fd.write("clean: " + self.TARGET_PREFIX + "clean\n\n");

		#
		# Generate all object recipes
		#

		self.makefile_fd.write(self.TARGET_PREFIX + "all: " + self.TARGET_PREFIX +  "all_o\n")

		if self.LIB_TARGET is not None:
			lt = self.LIB_TARGET
			if not lt.startswith("lib"):
				lt = "lib" + lt

			if not lt.endswith(".so"):
				lt += ".so"

			lt = os.path.join(self.OUTPUT_DIR,lt)

			self.makefile_fd.write("\t" + self.CXX + self.make_cxx_flags() + self.make_cxx_lib_flags() + " -o " + lt + " ")

			for f in self.SOURCE_FILES:
				self.makefile_fd.write(" " + self.make_object_file_name(f))

		elif self.EXE_TARGET is not None:
			self.makefile_fd.write("\t" + self.LD + self.make_cxx_link_flags() + " -o " + self.EXE_TARGET)

			for f in self.SOURCE_FILES:
				self.makefile_fd.write(" " + self.make_object_file_name(f))

			self.makefile_fd.write(self.make_cxx_lib_dir_flags() + self.make_cxx_link_lib_flags() + self.make_cxx_exe_flags() );
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
		print >>self.makefile_fd,"""
#
# This file is mechanically generated.  Any changes will most likely be lost.
#"""

		print >>self.makefile_fd,"# File generated on: " + datetime.datetime.now().isoformat()
		print >>self.makefile_fd,"#\n"


	def write_makefile_footer(self):
		"""
		Writes out the footer portion of the makefile
		"""
		print >>self.makefile_fd,"""
#
# EOF
#
		"""

	def init(self):
		"""
		Initializes the context instance
		"""

		if self.TAG is not None and len(self.TAG) > 0:
			self.TARGET_PREFIX = self.TAG + "_"

		if isinstance(self.INCLUDE_DIRS,tuple):
			self.INCLUDE_DIRS = list(self.INCLUDE_DIRS)

		self.makefile_fd = StringIO.StringIO()
		self.write_makefile_header()

		if self.RELATED_PROJECTS is not None:
			for p in self.RELATED_PROJECTS:
				print "Processing related project in: " + p

				ctx = import_project(p)

				if ctx is None:
					return False

				ctx.TOP_LEVEL = False

				for d in ctx.INCLUDE_DIRS:
					id = os.path.join(p,d)
					self.INCLUDE_DIRS += [id,]

				if ctx.LIB_TARGET is not None and len(ctx.LIB_TARGET) > 0:
					lib_file = SourceFile(ctx.LIB_TARGET)
					self.LIBRARIES.append(lib_file.base_name)

					self.LIB_DIRS.append(os.path.join(p,ctx.OUTPUT_DIR))




	def finalize(self):
		"""
		Finalizes the context instance
		"""
		self.makefile_fd.close()

	def __str__(self):
		return str(self.TAG) + ":"

########################################################

def import_project(_dir):
	"""
	Imports a VC.py project file from the specified directory
	@return An instance of the context
	"""

	# Check for existence of the module
	f = os.path.join(_dir,"VC.py")
	if not os.access(f,os.R_OK):
		print >>sys.stderr, "VC.py does not exist.  Please fix"
		return None

	# Save a copy of the system path
	old_path = list(sys.path)

	# Add the path of the module as the first element
	sys.path.insert(0,_dir)

	m = None

	try:
		m = importlib.import_module("VC")
	except Exception,e:
		print >>sys.stderr, "Failed to load configuration file VC.py: " + str(e)
		return None

	# Restore system path
	sys.path = list(old_path)
	ctx = m.vc_init()

	# Cleanup after ourselves because we may need to load VC.py for other projects.
	del m
	del sys.modules["VC"]

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
			print >>sys.stderr,"File not readable: " + f
			rc = False

	return rc

def generate_dependencies(_ctx):
	cmd = []

	cmd += [_ctx.CXX] +  _ctx.make_include_parms()

	cmd += _ctx.CXX_DEPEND_FLAGS + _ctx.CXX_FLAGS

	for f in _ctx.SOURCE_FILES:
		b = ""
		wcmd = cmd + ["-MT",_ctx.make_object_file_name(f),_ctx.make_source_file_name(f)]
		#print wcmd

		p = subprocess.Popen(wcmd,stdin=None,stderr=subprocess.PIPE,stdout=subprocess.PIPE)
		p.wait()

		if p.returncode != 0:
			for l in p.stderr:
				b += l

			print >>sys.stderr,"Failed to process dependencies, code: " + str(p.returncode)
			print >>sys.stderr,"cmd: " + " ".join(wcmd)
			print >>sys.stderr,b

			return False
		else:
			_ctx.makefile_fd.write("\n")
			for l in p.stdout:
				_ctx.makefile_fd.write(l)

			_ctx.makefile_fd.write("\tg++ " + " ".join(_ctx.make_include_parms()) + " " +  _ctx.make_cxx_flags() +  " -c " + _ctx.make_source_file_name(f) + " -o " + _ctx.make_object_file_name(f)  + "\n")

	return True

def process(_ctx):
	_ctx.init()

	if not check_source_files(_ctx):
		print >>sys.stderr,"Failed file check"
		sys.exit(-1)

	verify_output_paths(_ctx)

	_ctx.write_makefile()

	generate_dependencies(_ctx)

	_ctx.write_makefile_footer()

	make_str =  _ctx.makefile_fd.getvalue()

	_ctx.finalize()

	return make_str

sys.dont_write_bytecode = True


if __name__ == "__main__":

	print "Currently in: " + os.getcwd()
	ctx = import_project(os.getcwd())

	mstr = process(ctx)
	mfd = open("Makefile","wt")
	mfd.write(mstr)
	mfd.close()