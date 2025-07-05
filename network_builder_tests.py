import network_builder
import introcs

def test_convert_follower_count():

    print('testing convert_follow_counts')

    count = '1 M'
    expected = 1000000
    result = network_builder.convert_follower_count(count)
    introcs.assert_equals(expected, result)

    count = '5 K'
    expected = 5000
    result = network_builder.convert_follower_count(count)
    introcs.assert_equals(expected, result)

    count = '1500'
    expected = 1500
    result = network_builder.convert_follower_count(count)
    introcs.assert_equals(expected, result)

    count = '2.5 M'
    expected = 2500000
    result = network_builder.convert_follower_count(count)
    introcs.assert_equals(expected, result)

    count = '6 FOLLOWS'
    expected = 6
    result = network_builder.convert_follower_count(count)
    introcs.assert_equals(expected, result)

    count = 100
    expected = 100
    result = network_builder.convert_follower_count(count)
    introcs.assert_equals(expected, result)

    print('all tests passed for convert_follow_counts')


if __name__ == '__main__':
    test_convert_follower_count()

    print('all tests passed for sampling functions')