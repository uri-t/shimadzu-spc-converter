class SpcFile
  HEADER_ENTRIES = {sector_size_exp:       {offset: 30, size: 2},
                    short_sector_size_exp: {offset: 32, size: 2},
                    num_sat_sectors:       {offset: 44, size: 4},
                    root_sid:              {offset: 48, size: 4},
                    stream_size_cutoff:    {offset: 56, size: 4},
                    ssat_sid:              {offset: 60, size: 4},
                    num_ssat_sectors:      {offset: 64, size: 4},
                    msat_sid:              {offset: 68, size: 4},
                    num_msat_sectors:      {offset: 72, size: 4},
                    msat:                  {offset: 76, size: 436}}

  DIRECTORY_ENTRIES = {name:         {offset: 0,   size: 64},
                       name_size:    {offset: 64,  size: 2},
                       type:         {offset: 66,  size: 1},
                       color:        {offset: 67,  size: 1},
                       left_sib_id:  {offset: 68,  size: 4},
                       right_sib_id: {offset: 72,  size: 4},
                       child_id:     {offset: 76,  size: 4},
                       sid:          {offset: 116, size: 4},
                       size:         {offset: 120, size: 4}}
  DIRECTORY_SIZE = 128
  
  def initialize(fname)
    @fname = fname
  end

  def header
    if ! @header
      @header = {}
      HEADER_ENTRIES.keys.each do |k|
        offset = HEADER_ENTRIES[k][:offset]
        size = HEADER_ENTRIES[k][:size]
        unpacker = {2 => 's', 4 => 'l'}[size] || 'l*'
        @header[k] = File.binread(@fname, size, offset).unpack(unpacker)
        if @header[k].size == 1
          @header[k] = @header[k][0]
        end
      end
    end
    @header
  end

  def get_dir(dir_id)
    offset = DIRECTORY_SIZE*dir_id
    directory_stream = stream_list(header[:root_sid])

    sector_offset = offset/(2**header[:sector_size_exp])

    if sector_offset > directory_stream.size
      raise("This directory is outside the allotted space for directories")
    end

    sid = directory_stream[sector_offset]

    offset = offset % 2**header[:sector_size_exp]
    dir_offset = (sid+1)*2**header[:sector_size_exp]+offset

    dir = {}
    DIRECTORY_ENTRIES.keys.each do |k|
      entry_offset = DIRECTORY_ENTRIES[k][:offset]
      size  = DIRECTORY_ENTRIES[k][:size]
      dir[k] = File.binread(@fname, size, dir_offset+entry_offset).unpack('s')[0]
    end
    dir[:name] = File.binread(@fname, dir[:name_size], dir_offset).unpack('a*')[0].split("").map {|x| x.ord}.select{|x| x>=32}.map{|x| x.chr}.join
    return dir
  end

  # returns the SAT table as an array of sids in order
  def sat_sids
    sat_sids = []
    sat = header[:msat][0]
    while sat != -1
      sat_sids << sat
      sat =  header[:msat][sat]
    end

    # doesn't take into account the possibility of multiple MSAT sectors
    # I think this should only occur for files bigger than ~8MB
    if header[:num_msat_sectors] > 0
      raise("whoa there big file")
    end
    
    return sat_sids
  end

  # returns list of sector ids in the order in which they appear in the normal stream
  # reads from SAT table
  def stream_list(start_id)
    sids_raw = []
    sat_sids.each do |s|
      size = 2**header[:sector_size_exp]
      offset = (s+1)*size
      sids_raw.concat(File.binread(@fname, size, offset).unpack('l*'))
      
    end
    stream = []
    sid = start_id
    while sid > 0
      stream << sid
      sid = sids_raw[sid]
    end
    return stream
  end
end
