import os
import base64
import json
from loguru import logger

from fastapi import Request


async def get_redis(request: Request):
    return request.app.redis_pool


class BaseRedis:
    def __init__(self, redis_pool, base_key, id):
        """ Prepare everything we need and copy the relevant parts of the configuration
        """
        self.redis = redis_pool
        self.base_key = base_key
        self.id = id if id else base64.urlsafe_b64encode(os.urandom(9)).decode('utf-8')
        self.key = f"{self.base_key}:{self.__class__.__name__}:{self.id}"

    async def get_redis(self, subkey, *args, **kwargs):
        actual_key = f"{self.key}:{subkey}"
        value = await self.redis.get(actual_key, *args, **kwargs)
        return value

    async def set_redis(self, subkeys_values_dict):
        for subkey, value in subkeys_values_dict.items():
            actual_key = f"{self.key}:{subkey}"
            await self.redis.set(actual_key, value)

    async def get_redis_json(self, subkey):
        s = await self.get_redis(subkey, encoding='utf-8')
        data = json.loads(s) if s else None
        return data

    async def set_redis_json(self, subkey, data):
        s = json.dumps(data)
        await self.set_redis({subkey: s})


# Strongly inspired by JP's Blog: Automagically storing Python objects in Redis
# https://blog.jverkamp.com/2015/07/16/automagically-storing-python-objects-in-redis/

import json
#import redis

class RedisObject(object):
    """
    A base object backed by redis, which mainly adds an id.
    Generally, use RedisDict or RedisList rathen than this directly.
    """

    def __init__(self, redis_pool, id=None):
        """Create or load a RedisObject. 
        Redis host is always "redis", use docker/docker-compose."""
        self.redis = redis_pool

        self.id = id if id else base64.urlsafe_b64encode(os.urandom(9)).decode('utf-8')
        if ':' not in self.id:
            self.id = self.__class__.__name__ + ':' + self.id

    # def __bool__(self):
    #     """Test if an object currently exists"""
    #     return self.redis.exists(self.id)

    def __eq__(self, other):
        """Tests if two redis objects are equal (they have the same key)"""
        return self.id == other.id

    def __str__(self):
        """Return this object as a string for testing purposes."""
        return self.id

    def delete(self):
        """Delete this object from redis.
        Unfortunately, __del__ is called only on garbage collection which might be late."""
        self.redis.delete(self.id)

    @staticmethod
    def decode_value(type, value):
        """Decode a value if it is non-None, otherwise, decode with no arguments."""
        return type(value) if value else type()

    @staticmethod
    def encode_value(value):
        """Encode a value using json.dumps, with default = str"""
        return str(value)


class RedisDict(RedisObject):
    '''An equivalent to dict where all keys/values are stored in Redis.'''

    def __init__(self, id = None, fields = {}, defaults = None):
        '''
        Create a new RedisObject
        id: If specified, use this as the redis ID, otherwise generate a random ID.
        fields: A map of field name to type/construtor name used to read values from redis.
            Objects will be written with json.dumps with default = str, so override __str__ for custom objects.
            This should generally be set by the subobject's constructor.
        defaults: A map of field name to values to store when constructing the object.
        '''

        RedisObject.__init__(self, id)

        self.fields = fields

        if defaults:
            for key, val in defaults.items():
                self[key] = val

    def __getitem__(self, key):
        '''
        Load a field from this redis object.
        Keys that were not specified in self.fields will raise an exception.
        Keys that have not been set (either in defaults or __setitem__) will return the default for their type (if set)
        '''

        if key == 'id':
            return self.id

        if not key in self.fields:
            raise KeyError('{} not found in {}'.format(key, self))

        return RedisObject.decode_value(self.fields[key], self.redis.hget(self.id, key))

    def __setitem__(self, key, val):
        '''
        Store a value in this redis object.
        Keys that were not specified in self.fields will raise an exception.
        Keys will be stored with json.dumps with a default of str, so override __str__ for custom objects.
        '''

        if not key in self.fields:
            raise KeyError('{} not found in {}'.format(key, self))

        self.redis.hset(self.id, key, RedisObject.encode_value(val))

    def __iter__(self):
        '''Return (key, val) pairs for all values stored in this RedisDict.'''

        yield ('id', self.id.rsplit(':', 1)[-1])

        for key in self.fields:
            yield (key, self[key])
