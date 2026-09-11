from demo_target.component_b import retry_delay_seconds


def test_retry_delay_is_exponential_and_capped():
    assert retry_delay_seconds(0) == 1
    assert retry_delay_seconds(4) == 16
    assert retry_delay_seconds(9) == 32
