echo "Starting ... "
# Usage:
#   Pass either 'prod' or 'test' as an argument. E.g.,
#       ./deploy.sh prod
#   ...or...
#       ./deploy.sh test

# Configure destination folder where we put everything 
# and will be the working directory of the service process.
if [ "$1" == "local" ]; then
  DIR=$TRANSMITTER_LOCAL_DEPLOY_DIR 
elif [ "$1" == "test" ]; then
  DIR=/home/ras3005/boost/transmitter-test
elif  [ "$1" == "prod" ]; then
  DIR=/home/ras3005/boost/transmitter-prod
else
  echo "Usage: ./deploy.sh test \n or \n ./deploy.sh prod"
  exit 1
fi

echo $DIR

# Create the destination dir if it does not exist.
if [ ! -d "$DIR" ]; then
  mkdir $DIR
fi

# Check whether we're inside a virtualenv.
# (See https://stackoverflow.com/a/13864829)
if [ -z "${VIRTUAL_ENV+x}" ]; then
  echo "error: need to be inside a virtualenv. Ideally, create one in $DIR"
  exit 1
else 
  echo "virtualenv folder is: $VIRTUAL_ENV"
fi

# Create enclave folder if it doesn't exist. 
# See README.md for information on config file(s)
# that need to be put in the enclave folder.
if [ ! -d "$DIR/enclave" ]; then
  mkdir $DIR/enclave
fi

# Install/update supporting libraries from git into virtualenv.
#pip install -r ./requirements.txt --process-dependency-links --upgrade
pip install -r ./requirements.txt --upgrade --upgrade-strategy eager

# Copy core files into installation.
cp ./app/*.py $DIR
if [ "$1" == "test" ]; then
  cp ./starttest.sh $DIR
elif [ "$1" == "prod" ]; then
  cp ./startprod.sh $DIR
fi

# Create a log folder if it doesn't exist.
# Actually, this is now handled by smart_logger in the kickshaws library.
# if [ ! -d "$DIR/log" ]; then
#   mkdir $DIR/log
# fi

echo "Done!"

