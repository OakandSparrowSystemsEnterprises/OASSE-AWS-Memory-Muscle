from demo_target.component_a import retry_delay_seconds


def test_retry_delay_is_exponential_and_capped():
    assert retry_delay_seconds(0) == 1
    assert retry_delay_seconds(3) == 8
    assert retry_delay_seconds(8) == 32
