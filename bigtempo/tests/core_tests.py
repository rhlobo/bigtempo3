# -*- coding: utf-8 -*-


from bigtempo.tagselection import TagSelector
import unittest
from mockito import mock, when, any as anyx, verify

import bigtempo.utils as utils
import bigtempo.core as core


class TestDatasourceEngine_for_datasources_without_dependencies(unittest.TestCase):

    def setUp(self):
        def builder(cls):
            return self.builder_mock.build(cls)
        self.builder_mock = mock()

        def processing_task_factory(instance, deps, lookback):
            return self.processing_task_factory_mock.create(instance)
        self.processing_task_factory_mock = mock()

        self.engine = core.DatasourceEngine(builder, processing_task_factory)

        class _Task(object):

            def __init__(self, instance):
                self.instance = instance

        self.instances = []
        self.classes = []
        for i in range(3):
            @self.engine.datasource('REGISTERED_KEY_%i' % i)
            class _SampleDatasource(object):
                pass

            instance = _SampleDatasource()
            self.classes.append(_SampleDatasource)
            self.instances.append(instance)
            when(self.builder_mock).build(_SampleDatasource).thenReturn(instance)
            when(self.processing_task_factory_mock).create(instance).thenReturn(_Task(instance))

    def test_get_should_raise_error_when_reference_was_not_registered(self):
        self.assertRaises(KeyError, self.engine.get, 'NOT_REGISTERED_KEY')

    def test_get_should_not_raise_error_when_reference_was_registered(self):
        self.engine.get('REGISTERED_KEY_1')

    def test_get_should_not_use_builder_when_reference_was_not_registered(self):
        self.assertRaises(KeyError, self.engine.get, 'NOT_REGISTERED_KEY_1')
        verify(self.builder_mock, times=0).build(anyx())

    def test_get_should_use_builder_when_reference_was_registered(self):
        self.engine.get('REGISTERED_KEY_1')
        verify(self.builder_mock, times=1).build(anyx())

    def test_get_should_only_use_builder_once_for_a_registered_reference(self):
        for i in range(5):
            self.engine.get('REGISTERED_KEY_1')
        verify(self.builder_mock, times=1).build(anyx())

    def test_get_should_only_use_builder_once_for_each_registered_reference(self):
        for i in range(2):
            self.engine.get('REGISTERED_KEY_1')
        for i in range(2):
            self.engine.get('REGISTERED_KEY_2')
        self.engine.get('REGISTERED_KEY_1')
        verify(self.builder_mock, times=2).build(anyx())

    def test_get_should_use_processing_task_factory_in_each_call_for_registered_references(self):
        repetition = 3
        for i in range(repetition):
            self.engine.get('REGISTERED_KEY_1')
            self.engine.get('REGISTERED_KEY_2')
        verify(self.processing_task_factory_mock, times=repetition).create(self.instances[1])
        verify(self.processing_task_factory_mock, times=repetition).create(self.instances[2])


class TestDatasourceEngine_for_datasources_with_dependencies(unittest.TestCase):

    def setUp(self):
        def builder(cls):
            return self.builder_mock.build(cls)
        self.builder_mock = mock()

        def processing_task_factory(instance, deps, lookback):
            return self.processing_task_factory_mock.create(instance)
        self.processing_task_factory_mock = mock()

        self.engine = core.DatasourceEngine(builder, processing_task_factory)

        class _Task(object):

            def __init__(self, instance):
                self.instance = instance

        self.classes = []
        self.instances = []
        registered_keys = []
        for i in range(3):
            @self.engine.datasource('REGISTERED_KEY_%i' % i, dependencies=list(registered_keys))
            class _SampleDatasource(object):
                pass

            instance = _SampleDatasource()
            self.classes.append(_SampleDatasource)
            self.instances.append(instance)
            registered_keys.append('REGISTERED_KEY_%i' % i)
            when(self.builder_mock).build(_SampleDatasource).thenReturn(instance)
            when(self.processing_task_factory_mock).create(instance).thenReturn(_Task(instance))

    def test_get_should_use_builder_for_required_reference_and_for_its_dependency(self):
        self.engine.get('REGISTERED_KEY_1')
        verify(self.builder_mock, times=1).build(self.classes[1])
        verify(self.builder_mock, times=1).build(self.classes[0])

    def test_get_should_use_builder_for_required_reference_and_for_each_dependency(self):
        self.engine.get('REGISTERED_KEY_2')
        verify(self.builder_mock, times=1).build(self.classes[2])
        verify(self.builder_mock, times=1).build(self.classes[1])
        verify(self.builder_mock, times=1).build(self.classes[0])

    def test_get_should_only_use_builder_once_for_each_reference_including_dependencies(self):
        for i in range(5):
            self.engine.get('REGISTERED_KEY_1')
        verify(self.builder_mock, times=1).build(self.classes[1])
        verify(self.builder_mock, times=1).build(self.classes[0])

    def test_get_should_use_processing_task_factory_in_each_call_for_registered_references_including_dependencies(self):
        self.engine.get('REGISTERED_KEY_1')
        self.engine.get('REGISTERED_KEY_2')
        verify(self.processing_task_factory_mock, times=3).create(self.instances[0])
        verify(self.processing_task_factory_mock, times=2).create(self.instances[1])
        verify(self.processing_task_factory_mock, times=1).create(self.instances[2])


class TestDatasourceEngine_tag_related_behaviours_not_considering_tag_inference(unittest.TestCase):

    def setUp(self):
        self.TagSelector = core.tagselection.TagSelector
        self.tagSelectorMock = mock(core.tagselection.TagSelector)
        core.tagselection.TagSelector = utils.CallableMock(self.tagSelectorMock)
        when(self.tagSelectorMock).__call__(anyx()).thenReturn(self.tagSelectorMock)
        when(self.tagSelectorMock).register(...).thenReturn(None)

        self.TagManager = core.tagselection.TagManager
        self.tagManagerMock = mock(core.tagselection.TagManager)
        core.tagselection.TagManager = utils.CallableMock(self.tagManagerMock)
        when(self.tagManagerMock).__call__(anyx()).thenReturn(self.tagManagerMock)
        when(self.tagManagerMock).infere_tags(anyx()).thenReturn(set())
        when(self.tagManagerMock).evaluate_new_candidate(...).thenReturn(None)

        self.engine = core.DatasourceEngine()

    def tearDown(self):
        core.tagselection.TagManager = self.TagManager
        core.tagselection.TagSelector = self.TagSelector

    def test_register_datasource_should_instantiate_tag_selector_on_initialization(self):
        verify(self.tagSelectorMock, times=1).__call__(anyx())

    def test_register_datasource_should_trigger_tag_registration_on_tag_selector_passing_empty_set_when_no_tags_where_given(self):
        reference = 'REFERENCE'

        @self.engine.datasource(reference)
        class DatasourceWithTags(object):
            pass

        verify(self.tagSelectorMock, times=1).register(reference, set())

    def test_register_datasource_should_trigger_tag_registration_on_tag_selector_passing_given_list_as_set(self):
        reference = 'REFERENCE'
        expected_tags = ['tag1', 'tag2']

        @self.engine.datasource(reference, tags=expected_tags)
        class DatasourceWithTags(object):
            pass

        verify(self.tagSelectorMock, times=1).register(reference, set(expected_tags))

    def test_register_datasource_should_trigger_tag_registration_on_tag_selector_passing_given_set(self):
        reference = 'REFERENCE'
        expected_tags = set(['tag1', 'tag2'])

        @self.engine.datasource(reference, tags=expected_tags)
        class DatasourceWithTags(object):
            pass

        verify(self.tagSelectorMock, times=1).register(reference, expected_tags)


class TestDatasourceEngine_delegators(unittest.TestCase):

    def setUp(self):
        self.TagSelector = core.tagselection.TagSelector
        self.tagSelectorMock = mock(core.tagselection.TagSelector)
        core.tagselection.TagSelector = utils.CallableMock(self.tagSelectorMock)
        when(self.tagSelectorMock).__call__(anyx()).thenReturn(self.tagSelectorMock)
        when(self.tagSelectorMock).register(...).thenReturn(None)

        self.TagManager = core.tagselection.TagManager
        self.tagManagerMock = mock(core.tagselection.TagManager)
        core.tagselection.TagManager = utils.CallableMock(self.tagManagerMock)
        when(self.tagManagerMock).__call__(anyx()).thenReturn(self.tagManagerMock)
        when(self.tagManagerMock).infere_tags(anyx()).thenReturn(set())
        when(self.tagManagerMock).register(...).thenReturn(None)
        when(self.tagManagerMock).register_synched(...).thenReturn(None)

        self.engine = core.DatasourceEngine()

    def tearDown(self):
        core.tagselection.TagManager = self.TagManager
        core.tagselection.TagSelector = self.TagSelector

    def test_select_should_delegate_to_tag_selector(self):
        args = ['a', 'b', 'c']
        expected = object()

        when(self.tagSelectorMock).get(*args).thenReturn(expected)

        result = self.engine.select(*args)

        verify(self.tagSelectorMock, times=1).get(*args)
        assert expected is result

    def test_tags_should_delegate_to_tag_selector(self):
        args = ['a', 'b', 'c']
        expected = object()

        when(self.tagSelectorMock).tags(*args).thenReturn(expected)

        result = self.engine.tags(*args)

        verify(self.tagSelectorMock, times=1).tags(*args)
        assert expected is result

    def test_for_each_should_delegate_to_tagManager_register_method(self):
        selection = object()

        def function():
            pass

        self.engine.for_each(selection)(function)

        verify(self.tagManagerMock, times=1).register(function, selection)

    def test_for_synched_should_delegate_to_tagManager_register_synched_method(self):
        selection = object()

        def function():
            pass

        self.engine.for_synched(selection)(function)

        verify(self.tagManagerMock, times=1).register_synched(function, anyx())


class TestDatasourceEngine_tag_related_behaviours_considering_tag_inference(unittest.TestCase):

    def setUp(self):
        self.TagSelector = core.tagselection.TagSelector
        self.tagSelectorMock = mock(core.tagselection.TagSelector)
        when(self.tagSelectorMock).__call__(anyx()).thenReturn(self.tagSelectorMock)
        when(self.tagSelectorMock).register(...).thenReturn(None)
        core.tagselection.TagSelector = utils.CallableMock(self.tagSelectorMock)

        self.engine = core.DatasourceEngine()

    def tearDown(self):
        core.tagselection.TagSelector = self.TagSelector

    def test_register_datasource_should_trigger_tag_registration_with_reference_itself_as_a_tag(self):
        reference = 'REFERENCE'

        @self.engine.datasource(reference)
        class DatasourceWithTags(object):
            pass

        verify(self.tagSelectorMock, times=1).register(reference, set([reference]))

    def test_register_datasource_should_trigger_tag_registration_with_reference_itself_as_a_tag_plus_declared_tags(self):
        reference = 'REFERENCE'
        declared_tags = ['tag1', 'tag2']
        expected_tags = ['tag1', 'tag2', 'REFERENCE']

        @self.engine.datasource(reference, tags=declared_tags)
        class DatasourceWithTags(object):
            pass

        verify(self.tagSelectorMock, times=1).register(reference, set(expected_tags))

    def test_register_datasource_should_trigger_tag_registration_with_reference_itself_as_a_tag_plus_declared_tags_using_set(self):
        reference = 'REFERENCE'
        declared_tags = set(['tag1', 'tag2'])
        expected_tags = set(['tag1', 'tag2', 'REFERENCE'])

        @self.engine.datasource(reference, tags=declared_tags)
        class DatasourceWithTags(object):
            pass

        verify(self.tagSelectorMock, times=1).register(reference, expected_tags)

    def test_register_datasource_should_trigger_tag_registration_with_dependency_as_tag_when_datasources_has_one_dependency(self):
        reference = 'REFERENCE'

        @self.engine.datasource('REFERENCE_DEPENDENCY_A')
        class DatasourceDependencyA(object):
            pass

        @self.engine.datasource(reference,
                                dependencies=['REFERENCE_DEPENDENCY_A'],
                                tags=['tag1', 'tag2'])
        class Datasource(object):
            pass

        verify(self.tagSelectorMock, times=1).register(reference, set(['tag1', 'tag2', 'REFERENCE', '{REFERENCE_DEPENDENCY_A}']))

    def test_register_datasource_should_trigger_tag_registration_with_dependencies_as_tags_when_datasources_has_multiple_dependencies(self):
        reference = 'REFERENCE'
        expected_tags = set(['tag1', 'tag2', 'REFERENCE',
                             '{REFERENCE_DEPENDENCY_A}',
                             '{REFERENCE_DEPENDENCY_B}',
                             '{REFERENCE_DEPENDENCY_C}'])

        @self.engine.datasource('REFERENCE_DEPENDENCY_A')
        class DatasourceDependencyA(object):
            pass

        @self.engine.datasource('REFERENCE_DEPENDENCY_B')
        class DatasourceDependencyB(object):
            pass

        @self.engine.datasource('REFERENCE_DEPENDENCY_C')
        class DatasourceDependencyC(object):
            pass

        @self.engine.datasource(reference,
                                dependencies=['REFERENCE_DEPENDENCY_A', 'REFERENCE_DEPENDENCY_B', 'REFERENCE_DEPENDENCY_C'],
                                tags=['tag1', 'tag2'])
        class Datasource(object):
            pass

        verify(self.tagSelectorMock, times=1).register(reference, expected_tags)

    def test_register_datasource_should_trigger_tag_registration_with_dependencies_and_subdependencies_as_tags(self):
        reference = 'REFERENCE'
        expected_tags = set(['tag1', 'tag2', 'REFERENCE',
                             '{REFERENCE_DEPENDENCY_A}',
                             '{REFERENCE_DEPENDENCY_B}',
                             '{REFERENCE_DEPENDENCY_C}'])

        @self.engine.datasource('REFERENCE_DEPENDENCY_A')
        class DatasourceDependencyA(object):
            pass

        @self.engine.datasource('REFERENCE_DEPENDENCY_B',
                                dependencies=['REFERENCE_DEPENDENCY_A'])
        class DatasourceDependencyB(object):
            pass

        @self.engine.datasource('REFERENCE_DEPENDENCY_C',
                                dependencies=['REFERENCE_DEPENDENCY_B'])
        class DatasourceDependencyC(object):
            pass

        @self.engine.datasource(reference,
                                dependencies=['REFERENCE_DEPENDENCY_C'],
                                tags=['tag1', 'tag2'])
        class Datasource(object):
            pass

        print(self.engine._registrations[reference]['tags'])
        verify(self.tagSelectorMock, times=1).register(reference, expected_tags)

    def test_register_datasource_should_trigger_tag_registration_with_dependencies_and_its_tags_as_tags_when_datasources_has_dependencies_with_tags(self):
        reference = 'REFERENCE'
        expected_tags = set(['tag1', 'tag2', 'REFERENCE',
                            '{tag1A}', '{tag2A}', '{REFERENCE_DEPENDENCY_A}'])

        @self.engine.datasource('REFERENCE_DEPENDENCY_A',
                                tags=['tag1A', 'tag2A'])
        class DatasourceDependencyA(object):
            pass

        @self.engine.datasource(reference,
                                dependencies=['REFERENCE_DEPENDENCY_A'],
                                tags=['tag1', 'tag2'])
        class Datasource(object):
            pass

        print(self.engine._registrations[reference]['tags'])
        verify(self.tagSelectorMock, times=1).register(reference, expected_tags)

    def test_register_datasource_should_trigger_tag_registration_with_multiple_dependencies_and_its_tags_as_tags_when(self):
        reference = 'REFERENCE'
        expected_tags = set(['tag1', 'tag2', 'REFERENCE',
                             '{tag1A}', '{tag2A}', '{REFERENCE_DEPENDENCY_A}',
                             '{tag1B}', '{tag2B}', '{REFERENCE_DEPENDENCY_B}',
                             '{tag1C}', '{tag2C}', '{REFERENCE_DEPENDENCY_C}'])

        @self.engine.datasource('REFERENCE_DEPENDENCY_A',
                                tags=['tag1A', 'tag2A'])
        class DatasourceDependencyA(object):
            pass

        @self.engine.datasource('REFERENCE_DEPENDENCY_B',
                                tags=['tag1B', 'tag2B'])
        class DatasourceDependencyB(object):
            pass

        @self.engine.datasource('REFERENCE_DEPENDENCY_C',
                                tags=['tag1C', 'tag2C'])
        class DatasourceDependencyC(object):
            pass

        @self.engine.datasource(reference,
                                dependencies=['REFERENCE_DEPENDENCY_A', 'REFERENCE_DEPENDENCY_B', 'REFERENCE_DEPENDENCY_C'],
                                tags=['tag1', 'tag2'])
        class Datasource(object):
            pass

        print(self.engine._registrations[reference]['tags'])
        verify(self.tagSelectorMock, times=1).register(reference, expected_tags)

    def test_register_datasource_should_trigger_tag_registration_with_multiple_nested_dependencies_and_its_tags_as_tags(self):
        reference = 'REFERENCE'
        expected_tags = set(['tag1', 'tag2', 'REFERENCE',
                             '{tag1A}', '{tag2A}', '{REFERENCE_DEPENDENCY_A}',
                             '{tag1B}', '{tag2B}', '{REFERENCE_DEPENDENCY_B}',
                             '{tag1C}', '{tag2C}', '{REFERENCE_DEPENDENCY_C}'])

        @self.engine.datasource('REFERENCE_DEPENDENCY_A',
                                tags=['tag1A', 'tag2A'])
        class DatasourceDependencyA(object):
            pass

        @self.engine.datasource('REFERENCE_DEPENDENCY_B',
                                dependencies=['REFERENCE_DEPENDENCY_A'],
                                tags=['tag1B', 'tag2B'])
        class DatasourceDependencyB(object):
            pass

        @self.engine.datasource('REFERENCE_DEPENDENCY_C',
                                dependencies=['REFERENCE_DEPENDENCY_B'],
                                tags=['tag1C', 'tag2C'])
        class DatasourceDependencyC(object):
            pass

        @self.engine.datasource(reference,
                                dependencies=['REFERENCE_DEPENDENCY_C'],
                                tags=['tag1', 'tag2'])
        class Datasource(object):
            pass

        print(self.engine._registrations[reference]['tags'])
        verify(self.tagSelectorMock, times=1).register(reference, expected_tags)


class TestDatasourceEngine_tag_inference_and_declaration(unittest.TestCase):

    def setUp(self):
        self.TagManager = core.tagselection.TagManager

        self.tagManagerMock = mock(core.tagselection.TagManager)
        when(self.tagManagerMock).__call__(anyx(dict)).thenReturn(self.tagManagerMock)
        core.tagselection.TagManager = utils.CallableMock(self.tagManagerMock)

        self.engine = core.DatasourceEngine()

    def tearDown(self):
        core.tagselection.TagManager = self.TagManager

    def test_register_datasource_should_register_tags_based_on_declared_and_infered(self):
        reference = 'REFERENCE'
        infered_tags = set(['infered1', 'infered2'])
        declared_tags = set(['declared1', 'declared2'])

        when(self.tagManagerMock).infere_tags(reference).thenReturn(infered_tags)
        when(self.tagManagerMock).evaluate_new_candidate(...).thenReturn(None)

        @self.engine.datasource(reference,
                                tags=declared_tags)
        class Datasource(object):
            pass

        assert self.engine._registrations[reference]['tags'] == (infered_tags | declared_tags)
