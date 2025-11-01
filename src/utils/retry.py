"""リトライ処理ユーティリティ"""
import asyncio
import logging
from typing import Callable, Any, Optional

logger = logging.getLogger(__name__)


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 4.0,
    backoff_factor: float = 2.0,
    timeout: Optional[float] = None,
    retryable_errors: tuple = (Exception,),
    *args,
    **kwargs
) -> Any:
    """
    指数バックオフ付きリトライ処理
    
    Args:
        func: 実行する関数（非同期または同期）
        max_retries: 最大リトライ回数
        initial_delay: 初期遅延時間（秒）
        max_delay: 最大遅延時間（秒）
        backoff_factor: バックオフ係数
        timeout: タイムアウト時間（秒）
        retryable_errors: リトライ対象のエラー型
        *args, **kwargs: funcに渡す引数
    
    Returns:
        関数の実行結果
    
    Raises:
        最後の試行時のエラー
    """
    last_error = None
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            if timeout:
                return await asyncio.wait_for(
                    asyncio.ensure_future(func(*args, **kwargs)),
                    timeout=timeout
                )
            else:
                result = func(*args, **kwargs)
                if asyncio.iscoroutine(result):
                    return await result
                return result
        except retryable_errors as e:
            last_error = e
            
            if attempt < max_retries:
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries + 1} failed: {str(e)}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
                delay = min(delay * backoff_factor, max_delay)
            else:
                logger.error(f"All {max_retries + 1} attempts failed. Last error: {str(e)}")
        except Exception as e:
            # リトライ対象外のエラーは即座に再発生
            logger.error(f"Non-retryable error: {str(e)}")
            raise
    
    # すべてのリトライが失敗した場合
    raise last_error
