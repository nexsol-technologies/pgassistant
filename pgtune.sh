#!/usr/bin/env bash

KB=1024
MB=1048576
GB=1073741824

show_help() {
cat << EOF
Usage: ${0##*/} [-h] [-v PG_VERSION] [-t DB_TYPE] [-m TOTAL_MEM] [-u CPU_COUNT] [-c MAX_CONN] [-s STGE_TYPE]

This script is a bash port of PGTune (https://pgtune.leopard.in.ua).
It produces a postgresql.conf file based on supplied parameters.

  -h                  display this help and exit
  -v PG_VERSION       (optional) PostgreSQL version
                      accepted values: 9.5, 9.6, 10, 11, 12, 13, 14, 15, 16
                      default value: 15
  -t DB_TYPE          (optional) For what type of application is PostgreSQL used
                      accepted values: web, oltp, dw, desktop, mixed
                      default value: web
  -m TOTAL_MEM        (optional) how much memory can PostgreSQL use
                      accepted values: integer with unit ("MB" or "GB") between 1 and 9999 and greater than 512MB
                      default value: this script will try to determine the total memory and exit in case of failure
  -u CPU_COUNT        (optional) number of CPUs, which PostgreSQL can use
                      accepted values: integer between 1 and 9999
                      CPUs = threads per core * cores per socket * sockets
                      default value: this script will try to determine the CPUs count and exit in case of failure
  -c MAX_CONN         (optional) Maximum number of PostgreSQL client connections
                      accepted values: integer between 20 and 9999
                      default value: preset corresponding to db_type
  -s STGE_TYPE        (optional) Type of data storage device used with PostgreSQL
                      accepted values: hdd, ssd, san
                      default value: this script will try to determine the storage type (san not supported) and use hdd
                      value in case of failure.
EOF
}

_warn() {
  echo >&2 "[pgtune.sh] $*"
}

_input_error() {
  echo >&2 "[pgtune.sh] input error: $*"
  exit 1
}

_error() {
  echo >&2 "[pgtune.sh] error: $*"
  exit 2
}

get_total_ram () {
  local total_ram=0
  if [[ -z $total_ram ]] || [[ "$total_ram" -eq "0" ]]
  then
    _error "cannot detect total memory size, terminating script. Please supply -m TOTAL_MEM."
  fi
  echo $total_ram
}

get_cpu_count () {
  local cpu_count=$(nproc --all)
  if [[ -z $cpu_count ]] || [[ "$cpu_count" -eq "0" ]]
  then
    _error "cannot detect cpu count, terminating script. Please supply -u CPU_COUNT."
  fi
  echo $cpu_count
}

get_disk_type () {  
  disk_type="sdd"

  echo $disk_type
}

set_db_default_values() {
  case "$db_version" in
    "9.5")
      max_worker_processes=8
      ;;
    "9.6")
      max_worker_processes=8
      max_parallel_workers_per_gather=0
      ;;
    "10" | "11" | "12" | "13" | "14" | "15" | "16" | "17")
      max_worker_processes=8
      max_parallel_workers_per_gather=2
      max_parallel_workers=8
      ;;
    *)
      _error "unknown PostgreSQL version, cannot continue"
      ;;
  esac
}

set_shared_buffers() {
  case "$db_type" in
    "web")
      shared_buffers=$(( $total_mem/4 ))
      ;;
    "oltp")
      shared_buffers=$(( $total_mem/4 ))
      ;;
    "dw")
      shared_buffers=$(( $total_mem/4 ))
      ;;
    "desktop")
      shared_buffers=$(( $total_mem/16 ))
      ;;
    "mixed")
      shared_buffers=$(( $total_mem/4 ))
      ;;
    *)
      _error "unknown db_type, cannot calculate shared_buffers"
      ;;
  esac
}

set_effective_cache_size() {
  case "$db_type" in
    "web")
      effective_cache_size=$(( $total_mem*3/4 ))
      ;;
    "oltp")
      effective_cache_size=$(( $total_mem*3/4 ))
      ;;
    "dw")
      effective_cache_size=$(( $total_mem*3/4 ))
      ;;
    "desktop")
      effective_cache_size=$(( $total_mem/4 ))
      ;;
    "mixed")
      effective_cache_size=$(( $total_mem*3/4 ))
      ;;
    *)
      _error "unknown db_type, cannot calculate effective_cache_size"
      ;;
  esac
}

set_maintenance_work_mem() {
  case "$db_type" in
    "web")
      maintenance_work_mem=$(( $total_mem/16 ))
      ;;
    "oltp")
      maintenance_work_mem=$(( $total_mem/16 ))
      ;;
    "dw")
      maintenance_work_mem=$(( $total_mem/8 ))
      ;;
    "desktop")
      maintenance_work_mem=$(( $total_mem/16 ))
      ;;
    "mixed")
      maintenance_work_mem=$(( $total_mem/16 ))
      ;;
    *)
      _error "unknown db_type, cannot calculate maintenance_work_mem"
      ;;
  esac
  local mem_limit=$(( 2 * $GB / $KB ))
  if [ "$maintenance_work_mem" -gt "$mem_limit" ]
  then
    maintenance_work_mem=$mem_limit
  fi
}

set_checkpoint_segments() {
  if [ ${db_version%.*} -le 9 ] && [ ${db_version//./} -lt 95 ]
  then
    case "$db_type" in
      "web")
        checkpoint_segments=32
        ;;
      "oltp")
        checkpoint_segments=64
        ;;
      "dw")
        checkpoint_segments=128
        ;;
      "desktop")
        checkpoint_segments=3
        ;;
      "mixed")
        checkpoint_segments=32
        ;;
      *)
        _error "unknown db_type, cannot calculate checkpoint_segments"
        ;;
    esac
  else
    case "$db_type" in
      "web")
        min_wal_size=$(( 1024 * $MB / $KB ))
        max_wal_size=$(( 4096 * $MB / $KB ))
        ;;
      "oltp")
        min_wal_size=$(( 2048 * $MB / $KB ))
        max_wal_size=$(( 8192 * $MB / $KB ))
        ;;
      "dw")
        min_wal_size=$(( 4096 * $MB / $KB ))
        max_wal_size=$(( 16384 * $MB / $KB ))
        ;;
      "desktop")
        min_wal_size=$(( 100 * $MB / $KB ))
        max_wal_size=$(( 2048 * $MB / $KB ))
        ;;
      "mixed")
        min_wal_size=$(( 1024 * $MB / $KB ))
        max_wal_size=$(( 4096 * $MB / $KB ))
        ;;
      *)
        _error "unknown db_type, cannot calculate min_wal_size"
        ;;
    esac
  fi
}

set_checkpoint_completion_target() {
  # based on https://github.com/postgres/postgres/commit/bbcc4eb2
  checkpoint_completion_target=0.9
}

set_wal_buffers() {
  # Follow auto-tuning guideline for wal_buffers added in 9.1, where it's
  # set to 3% of shared_buffers up to a maximum of 16MB.    
  wal_buffers=$(( 3 * $shared_buffers / 100 ))
  local max_wal_buffers=$(( 16 * $MB / $KB ))
  if [ "$wal_buffers" -gt "$max_wal_buffers" ]
  then
    wal_buffers=$max_wal_buffers
  fi
  # It's nice if wal_buffers is an even 16MB if it's near that number. Since
  # that is a common case on Windows, where shared_buffers is clipped to 512MB,
  # round upwards in that situation
  local near_max_wal_buffers=$(( 14 * MB / KB ))
  if [ "$wal_buffers" -gt "$near_max_wal_buffers" ] && [ "$wal_buffers" -lt "$max_wal_buffers" ]
  then
    wal_buffers=$max_wal_buffers
  fi
  # if less, than 32 kb, than set it to minimum
  if [ "$wal_buffers" -lt 32 ]
  then
    wal_buffers=32
  fi
}

set_default_statistics_target() {
  case "$db_type" in
    "web")
      default_statistics_target=100
      ;;
    "oltp")
      default_statistics_target=100
      ;;
    "dw")
      default_statistics_target=500
      ;;
    "desktop")
      default_statistics_target=100
      ;;
    "mixed")
      default_statistics_target=100
      ;;
    *)
      _error "unknown db_type, cannot calculate default_statistics_target"
      ;;
  esac
}

set_random_page_cost() {
  case "$storage_type" in
    "ssd")
      random_page_cost=1.1
      ;;
    "hdd")
      random_page_cost=4
      ;;
    "san")
      random_page_cost=1.1
      ;;
    *)
      _error "unknown storage_type, cannot calculate random_page_cost"
      ;;
  esac
}

set_effective_io_concurrency() {
  case "$storage_type" in
    "ssd")
      effective_io_concurrency=200
      ;;
    "hdd")
      effective_io_concurrency=2
      ;;
    "san")
      effective_io_concurrency=300
      ;;
    *)
      _error "unknown storage_type, cannot calculate effective_io_concurrency"
      ;;
  esac
}

set_parallel_settings() {
  declare -Ag parallel_settings
  if [ "$cpu_num" -lt 2 ] || ( [ ${db_version%.*} -le 9 ] && [ ${db_version//./} -lt 95 ] )
  then
    return 0
  fi
  parallel_settings[max_worker_processes]="$cpu_num"
  if [ "${db_version//./}" -ge "96" ] || [ ${db_version%.*} -ge 10 ]
  then
    workers_per_gather=$(( $cpu_num / 2 ))
    if [ $workers_per_gather -gt 4 ] && [[ "$db_type" != "dw" ]]
    then
      workers_per_gather=4
    fi
    parallel_settings[max_parallel_workers_per_gather]="$workers_per_gather"
  fi
  if [ ${db_version%.*} -ge 10 ]
  then
    parallel_settings[max_parallel_workers]="$cpu_num"
  fi
  if [ ${db_version%.*} -ge 11 ]
  then
    maintenance_workers=$(( $cpu_num / 2 ))
    if [ $maintenance_workers -gt 4 ]
    then
      maintenance_workers=4
    fi
    parallel_settings[max_parallel_maintenance_workers]="$maintenance_workers"
  fi
}

set_work_mem() {
  parallel_for_work_mem=1
  if [ "${#parallel_settings[@]}" -gt "0" ]
  then
    if [[ ${parallel_settings[max_parallel_workers_per_gather]} ]] 
    then
      parallel_for_work_mem=${parallel_settings[max_parallel_workers_per_gather]}
    fi
  elif [ ! -z ${max_parallel_workers_per_gather+x} ]
  then
    parallel_for_work_mem=$max_parallel_workers_per_gather
  fi
  work_mem_value=$(( ($total_mem - $shared_buffers) / ($conn_nb * 3) / $parallel_for_work_mem ))
  case "$db_type" in
    "web")
      work_mem=$work_mem_value
      ;;
    "oltp")
      work_mem=$work_mem_value
      ;;
    "dw")
      work_mem=$(( $work_mem_value/2 ))
      ;;
    "desktop")
      work_mem=$(( $work_mem_value/6 ))
      ;;
    "mixed")
      work_mem=$(( $work_mem_value/2 ))
      ;;
    *)
      _error "unknown db_type, cannot calculate work_mem"
      ;;
  esac
  if [ $work_mem -lt 64 ]
  then
    work_mem=64
  fi
}

format_value() {
  with_space=${2:-0}
  if [[ $with_space -eq "1" ]]
  then
    space=" "
  else
    space=""
  fi
  if [ $(( $1 % $MB )) -eq 0 ]
  then
    formatted_value=$(( $1 / $MB ))$space"GB"
    echo $formatted_value
  elif [ $(( $1 % $KB )) -eq 0 ]
  then
    formatted_value=$(( $1 / $KB ))$space"MB"
    echo $formatted_value
  else
    formatted_value=$1$space"kB"
    echo $formatted_value
  fi
}

total_mem=0 || exit $?
cpu_num=0 || exit $?
storage_type=$(get_disk_type)
conn_nb=0
db_type="web"
db_version=15

while getopts "hv:t:m:u:c:s:" opt; do
  case $opt in
    h)
      show_help
      exit 0
      ;;
    v)
      v=$OPTARG
      if [ $v != "9.5" ] && \
      [ $v != "9.6" ] && \
      [ $v != "10" ] && \
      [ $v != "11" ] && \
      [ $v != "12" ] && \
      [ $v != "13" ] && \
      [ $v != "14" ] && \
      [ $v != "15" ] && \
      [ $v != "16" ] && \
      [ $v != "17" ]
      then
        _input_error "$v is not a valid PostgreSQL version number"
      fi
      db_version=$v
      ;;
    t)                        
      t=$OPTARG
      if [ $t != "web" ] && \
      [ $t != "oltp" ] && \
      [ $t != "dw" ] && \
      [ $t != "desktop" ] && \
      [ $t != "mixed" ]
      then
        _input_error "$t is not a valid database type identifier" 
      fi
      db_type="$t"
      ;;
    m)                        
      m=$OPTARG
      if [[ $m == *"MB"* ]]
      then
        ram=${m%"MB"}
        if [ "$ram" -lt "512" ] || [ "$ram" -gt "9999" ]
        then
          _input_error "total memory in MB must be greater than or equal to 512MB and less than or equal to 9999MB" 
        fi
        ram=$(( $ram*$KB ))
      elif [[ $m == *"GB"* ]]
      then
        ram=${m%"GB"}
        if [ "$ram" -lt "1" ] || [ "$ram" -gt "9999" ]
        then
          _input_error "total memory in GB must be greater than or equal to 1GB and less than or equal to 9999GB"
        fi
        ram=$(( $ram*$MB ))
      else
        _input_error "$m does not contain a valid unit identifier (use MB or GB)"
      fi
      total_mem="$ram"
      ;;
    u)
      u=$OPTARG
      if [ "$u" -lt "1" ] || [ "$u" -gt "9999" ]
      then
        _input_error  "CPU count must be greater than or equal to 1 and less than or equal to 9999"
      fi
      cpu_num=$u
      ;;
    c)
      c=$OPTARG
      if [ "$c" -lt "20" ] || [ "$c" -gt "9999" ]
      then
        _input_error "connections number be greater than or equal to 1 and less than or equal to 9999"
      fi
      conn_nb=$c
      ;;
    s)
      s=$OPTARG
      if [ $s != "hdd" ] && \
      [ $s != "ssd" ] && \
      [ $s != "san" ]
      then
        _input_error "$s is not a valid storage type identifier"
      fi
      storage_type="$s"
      ;;
    *)
      show_help >&2
      exit 2
      ;;
  esac
done

if [ $conn_nb -eq "0" ]
then
  case $db_type in
  "web")
    conn_nb=200
    ;;
  "oltp")
    conn_nb=300
    ;;
  "dw")
    conn_nb=40
    ;;
  "desktop")
    conn_nb=20
    ;;
  "mixed")
    conn_nb=100
    ;;
  *)
    conn_nb=20
    ;;
  esac
fi 

set_db_default_values || exit $?
set_shared_buffers || exit $?
set_effective_cache_size || exit $?
set_maintenance_work_mem || exit $?
set_checkpoint_segments || exit $?
set_checkpoint_completion_target
set_wal_buffers
set_default_statistics_target || exit $?
set_random_page_cost || exit $?
set_effective_io_concurrency || exit $?
set_parallel_settings
set_work_mem || exit $?

echo "max_connections == "$conn_nb
echo "shared_buffers == "$(format_value $shared_buffers)
echo "effective_cache_size == "$(format_value $effective_cache_size)
echo "maintenance_work_mem == "$(format_value $maintenance_work_mem)
echo "checkpoint_completion_target == "$checkpoint_completion_target
echo "wal_buffers == "$(format_value $wal_buffers)
echo "default_statistics_target == "$default_statistics_target
echo "random_page_cost == "$random_page_cost
echo "effective_io_concurrency == "$effective_io_concurrency
echo "work_mem == "$(format_value $work_mem)
echo "min_wal_size == "$(format_value $min_wal_size)
echo "max_wal_size == "$(format_value $max_wal_size)
echo "huge_pages == off"

for key in "${!parallel_settings[@]}"
do 
  echo $key" == "${parallel_settings[$key]}
done
if [ ! -z ${checkpoint_segments+x}]
then
  echo "checkpoint_segments == "$checkpoint_segments
fi

unset set_parallel_settings