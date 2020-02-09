require_relative 'spc_file.rb'

spc = SpcFile.new('tests/09.spc')

puts spc.header
puts spc.get_dir(0)
puts spc.get_dir(1)
puts spc.get_dir(2)
puts spc.get_dir(3)
puts spc.get_dir(4)
puts spc.get_dir(5)
puts spc.get_dir(7)
puts spc.get_dir(8)
puts spc.get_dir(12)
puts spc.get_dir(13)
puts spc.get_dir(14)
puts spc.get_dir(15)
puts spc.get_dir(16)
puts spc.get_dir(20)

